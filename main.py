"""Browser entry for pygbag. Also runs with: python main.py"""

import asyncio

import pygame.mixer

from pingpong.game import main

asyncio.run(main())
