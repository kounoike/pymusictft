#!/usr/bin/python
# coding: utf-8
# 日本語です

import pygame
import pygame.gfxdraw
import mpd
import mutagen
import mutagen.flac
import mutagen.mp3
import mutagen.mp4
import mutagen.asf
import struct
import os
import time
import threading
import logging
from cStringIO import StringIO
import RPi.GPIO as GPIO
from signal import alarm, signal, SIGALRM, SIGKILL

logger = logging.getLogger('pymusictft')
logger.setLevel(10)
fh = logging.FileHandler('/tmp/pymusictft.log')
formatter = logging.Formatter('%(asctime)s:%(lineno)d:%(levelname)s:%(message)s')
fh.setFormatter(formatter)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)
#logger.addHandler(fh)
logger.addHandler(sh)
logger.info("start app")

os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV', '/dev/fb1')

class pymusictft:
    BASE_DIR = "/var/lib/mpd/music"
    INPUT_PORTS = [17, 22, 23, 27]
    FPS = 60
    SCROLL = 1
    FONT = "mikachanp" # "motoyalcedar" #"motoyalmaru" #"takaopgothic" # "vlgothic"
    TEXT_SIZE = 28
    screen = None
    size = None
    client = None
    current_title = None
    current_state = None
    font = None
    bg_surface = None
    text_surface = None
    img_surface = None
    text_position = 0
    is_pause = False
    noimg_surface = None
    is_show = True
    scroll_rect = None
    img_rect = None
    update_rects = []

    def __init__(self):
        "Initialize a new pygame screen using /dev/fb1"
        #raise Exception("TEST EXCEPTION")
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.INPUT_PORTS, GPIO.IN, GPIO.PUD_UP)

        logger.info("init()")
        pygame.init()
        logger.info("init() done.")

        logger.info("display.init()")
        pygame.display.init()
        logger.info("display.init() done.")
        pygame.mixer.quit()
        pygame.mouse.set_visible(False)

        self.size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        logger.info("set_mode()")
        class Alarm(Exception):
            pass
        def alarm_handler(signum, frame):
            raise Alarm
        signal(SIGALRM, alarm_handler)
        alarm(1)
        try:
            self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN)
        except Alarm:
            raise KeyboardInterrupt
        alarm(0)
        logger.info("set_mode() done.")
        self.screen.fill((180, 180, 180))
        pygame.display.update()

        pygame.font.init()
        self.font = pygame.font.SysFont(self.FONT, self.TEXT_SIZE)
        self.text_surface = self.font.render(u"テスト", True, (0, 0, 0))
        font2 = pygame.font.SysFont(self.FONT, 48)
        self.noimg_surface = font2.render(u"NO IMAGE", True, (255, 255, 255), (0, 0, 0))
        self.scroll_rect = pygame.rect.Rect(0, self.size[1] - self.text_surface.get_height(), self.size[0], self.text_surface.get_height())
        self.img_rect = pygame.rect.Rect(0, 0, self.size[0], self.size[1] - self.text_surface.get_height())

        self.client = mpd.MPDClient()
        self.client.connect("localhost", 6600)
        logger.info("__init__ done.")
    def __del__(self):
        pygame.quit()

    def update_scroll(self):
        pygame.gfxdraw.box(self.screen, self.scroll_rect, (20, 20, 20))
        self.screen.blit(self.text_surface, (self.text_position, self.size[1] - self.text_surface.get_height()))
        self.update_rects.append(self.scroll_rect)


    def update_surface(self):
        if not self.is_show:
            self.screen.fill((0, 0, 0))
            w = 25
            x1 = self.size[0] - 2 * w
            x2 = self.size[0] - w
            x3 = self.size[0]
            y1 = self.size[1] - w
            y2 = self.size[1]
            y3 = self.size[1] - w
            pygame.gfxdraw.filled_trigon(self.screen, x1, y1, x2, y2, x3, y3, (180, 180, 180))
            return
        self.screen.fill((40, 40, 40))

    def update_albumart(self):
        status = self.client.status()
        state = status["state"]

        song = self.client.currentsong()
        title = song["title"].decode("utf-8")
        if title == self.current_title and state == self.current_state:
            return

        self.current_title = title
        self.current_state = state
        self.is_pause = state == "pause"

        audio = mutagen.File(os.path.join(self.BASE_DIR, song["file"]))
        art = None
        if type(audio) == mutagen.flac.FLAC:
            if len(audio.pictures) > 0:
                art = audio.pictures[0].data
        elif type(audio) == mutagen.mp4.MP4:
            if len("covr" in audio and audio["covr"]) > 0:
                art = audio["covr"][0]
        elif type(audio) == mutagen.asf.ASF:
            if "WM/Picture" in audio and len(audio["WM/Picture"]) > 29:
                art = audio["WM/Picture"][0].value[29:]
        elif type(audio) == mutagen.mp3.MP3:
            if "APIC:thumbnail" in audio and len(audio["APIC:thumnail"]) > 0:
                art = audio["APIC:thumnail"].data

        h = self.size[1] - self.text_surface.get_height()
        x = (self.size[0] - h) / 2

        if art is None:
            # print song["file"], "doesn't contains album art!"
            self.img_surface = self.noimg_surface
        else:
            io = StringIO(art)
            self.img_surface = pygame.transform.smoothscale(pygame.image.load(io), (h, h))
        self.text_surface = self.font.render(self.current_title, True, (240, 240, 240))
        self.update_scroll()

        if self.is_pause:
            self.screen.fill((40, 40, 40))
            self.img_surface.set_alpha(200)
            self.screen.blit(self.img_surface, (x, 0))
            self.screen.blit(self.text_surface, (0, self.size[1] - self.text_surface.get_height()))
            cx = self.size[0] / 2
            cw = 10
            pw = 25
            ph = 50
            pt = 80
            pygame.draw.rect(self.screen,(255, 255, 255), pygame.rect.Rect(cx - cw - pw, pt , pw, ph))
            pygame.draw.rect(self.screen,(255, 255, 255), pygame.rect.Rect(cx +cw, pt , pw, ph))
        else:
            self.screen.fill((40, 40, 40))
            self.img_surface.set_alpha(255)
            self.screen.blit(self.img_surface, (x, 0))
        self.update_rects.append(self.img_rect)
    
    def _get_size(self, img):
        parser = ImageFile.Parser()
        parser.feed(img)
        return parser.image.size

    def main(self):
        clock = pygame.time.Clock()
        count = 0

        prev_inputs = []
        self.update_albumart()

        while True:
            clock.tick(self.FPS)
            if count == self.FPS:
                count = 0
                self.update_albumart()
            count += 1

            if not self.is_pause:
                self.text_position -= self.SCROLL
                if self.text_position < -self.text_surface.get_width():
                    self.text_position = self.size[0]
            self.update_scroll()

            inputs = map(lambda x: 1 - GPIO.input(x), self.INPUT_PORTS)
            if inputs != prev_inputs and sum(inputs) == 1:
                cmd = inputs.index(1)
                # pause
                if cmd == 0:
                    self.client.pause()
                    self.update_albumart()
                # start of this music
                elif cmd == 1:
                    self.client.seekcur(0)
                # next music
                elif cmd == 2:
                    self.client.next()
                    time.sleep(0.1)
                    self.update_albumart()
                # do nothing...?
                elif cmd == 3:
                    self.is_show = not self.is_show
            prev_inputs = inputs
            pygame.display.update(self.update_rects)
            self.update_rects = []



if __name__ == "__main__":
  try:
    app = pymusictft()
    app.main()
  except Exception as e:
    pygame.quit()
    logger.error(e)

