#!/usr/bin/env python

"""
Module Docstring
"""

import inspect  #for debug
import random
import pygame
from pygame.locals import *

__version__ = "0.1"
__all__ = ["Chip8"]

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RATIO = 10

bgcolor = BLACK
fgcolor = WHITE

# Keypad                   Keyboard
# +-+-+-+-+                +-+-+-+-+
# |1|2|3|C|                |1|2|3|4|
# +-+-+-+-+                +-+-+-+-+
# |4|5|6|D|                |Q|W|E|R|
# +-+-+-+-+       =>       +-+-+-+-+
# |7|8|9|E|                |A|S|D|F|
# +-+-+-+-+                +-+-+-+-+
# |A|0|B|F|                |Z|X|C|V|
# +-+-+-+-+                +-+-+-+-+
key_map = [
        K_x, K_1, K_2, K_3, #0, 1, 2, 3
        K_q, K_w, K_e, K_a, #4, 5, 6, 7
        K_s, K_d, K_z, K_c, #8, 9, A, B
        K_4, K_r, K_f, K_v, #C, D, E, F
        ]

class Errno:
    ENONE = 0x0
    # pc overflow
    EPCOF = 0x1
    # pc underflow
    EPCUF = 0x2
    # stack overflow
    ESTOF = 0x3,
    # stack underflow
    ESTUF = 0x4
    # bad opcode
    EBDOP = 0x5
    # not implemented
    ENIMP = 0x6
    # segmentation fault
    ESEGV = 0x7
    # user quit
    EUSRQ = 0x8

class Chip8:
    """Chip8 virtual machine"""

    def load_font(self):
        self.memory[0:80] = [
            0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
            0x20, 0x60, 0x20, 0x20, 0x70, # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
            0x90, 0x90, 0xF0, 0x10, 0x10, # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
            0xF0, 0x10, 0x20, 0x40, 0x40, # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90, # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
            0xF0, 0x80, 0x80, 0x80, 0xF0, # C
            0xE0, 0x90, 0x90, 0x90, 0xE0, # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
            0xF0, 0x80, 0xF0, 0x80, 0x80, # F 
        ]

    def load_rom(self, rom):
        romfile = file(rom, 'r')
        pos = 0x200
        while True:
            x = romfile.read(1)
            if x == '':
                break
            else:
                self.memory[pos] = ord(x)
                pos += 1

    def dump_memory(self):
        for x in range(0, 4096/16):
            line = ["{:02x}".format(v) for v in self.memory[(x*16):(x+1)*16]]
            print "0x{:03x}: ".format(x * 16) + " ".join(line)

    def draw_pixel(self, pixel, x, y):
        if pixel == 1:
            color = fgcolor
        else:
            color = bgcolor
        self.screen.fill(color, ((x*RATIO, y*RATIO), (RATIO, RATIO)))

    def clear_screen(self):
        self.screen.fill(bgcolor, ((0, 0), (64*RATIO, 32*RATIO)))

    def __init__(self, romfile):
        # general registers: 8-bit wide
        self.reg = [0 for x in range(0, 16)]
        # address register: 16-bit wide
        self.I = 0
        # stack: max depth 16, initial 0
        self.stack = []
        # memory
        self.memory = [0 for x in range(0, 4096)]
        # key state: 1 for pressed, otherwise 0
        self.key = [0 for x in range(0, 16)]
        # delay timer
        self.delay_timer = 0
        # sound timer
        self.sound_timer = 0
        # error number
        self.errno =  Errno.ENONE
        # load font to [0:0x50]
        self.load_font()
        # load program at 0x200
        self.load_rom(romfile)
        # pc
        self.pc = 0x200
        # opcode
        self.opcode = 0
        # init screen
        pygame.init()
        # 1x1 block is RATIOxRATIO
        size = (64*RATIO, 32*RATIO)
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Chip-8 Screen")
        # clear screen
        self.pixels = [[0 for x in range(0,64)] for y in range(0,32)]
        self.clear_screen()
        pygame.display.flip()
        # set frequency
        self.clock = pygame.time.Clock()

    def op_0(self):
        if self.opcode == 0xe0:
            # 00E0: Clear the screen.
            self.pixels = [[0 for x in range(0,64)] for y in range(0,32)]
            self.clear_screen()
            pygame.display.flip()
        elif self.opcode == 0xee:
            # 00EE: Returns from a subroutine.
            if len(self.stack) == 0:
                print "there is no caller on stack"
            else:
                self.pc = self.stack[-1]
                del self.stack[-1]
        else:
            # 0NNN: Calls RCA 1802 program at address NNN. Not necessary for most ROMs.
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def op_1(self):
        # 1NNN: Jumps to address NNN.
        self.pc = self.opcode & 0xfff

    def op_2(self):
        # 2NNN: Calls subroutine at NNN.
        if len(self.stack) == 16:
            print "the stack is full"
        else:
            self.stack.append(self.pc)
            self.pc = self.opcode & 0xfff

    def op_3(self):
        # 3XNN: Skips the next instruction if VX equals NN.
        vx = (self.opcode & 0x0f00) >> 8
        nn = self.opcode & 0xff
        if self.reg[vx] == nn:
            self.pc += 2

    def op_4(self):
        # 4NNN: Skips the next instruction if VX doesn't equal NN.
        vx = (self.opcode & 0x0f00) >> 8
        nn = self.opcode & 0xff
        if self.reg[vx] != nn:
            self.pc += 2

    def op_5(self):
        if self.opcode & 0xf == 0:
            # 5XY0: Skips the next instruction if VX equals VY.
            vx = (self.opcode & 0x0f00) >> 8
            vy = (self.opcode & 0x00f0) >> 4
            if self.reg[vx] == self.reg[vy]:
                self.pc += 2
        else:
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def op_6(self):
        # 6XNN: Sets VX to NN.
        vx = (self.opcode & 0x0f00) >> 8
        nn = self.opcode & 0xff
        self.reg[vx] = nn

    def op_7(self):
        # 7XNN: Adds NN to VX.
        vx = (self.opcode & 0x0f00) >> 8
        nn = self.opcode & 0xff
        self.reg[vx] = (self.reg[vx] + nn) & 0xff

    def op_8(self):
        subop = self.opcode & 0xf
        vx = (self.opcode & 0x0f00) >> 8
        vy = (self.opcode & 0x00f0) >> 4
        if subop == 0:
            # 8XY0: Sets VX to the value of VY
            self.reg[vx] = self.reg[vy]
        elif subop == 1:
            # 8XY1: Sets VX to VX or VY.
            self.reg[vx] |= self.reg[vy]
        elif subop == 2:
            # 8XY2: Sets VX to VX and VY.
            self.reg[vx] &= self.reg[vy]
        elif subop == 3:
            # 8XY3: Sets VX to VX xor VY.
            self.reg[vx] ^= self.reg[vy]
        elif subop == 4:
            # 8XY4: Adds VY to VX. VF is set to 1 when there's a carry, 
            # and to 0 when there isn't.
            self.reg[vx] += self.reg[vy]
            if self.reg[vx] > 0xff:
                self.reg[0xf] = 1
                self.reg[vx] &= 0xff
            else:
                self.reg[0xf] = 0
        elif subop == 5:
            # 8XY5: VY is subtracted from VX. VF is set to 0 when 
            # there's a borrow, and 1 when there isn't.
            if self.reg[vx] >= self.reg[vy]:
                self.reg[vx] -= self.reg[vy]
                self.reg[0xf] = 1
            else:
                self.reg[vx] = self.reg[vx] + 0x100 - self.reg[vy]
                self.reg[0xf] = 0
        elif subop == 6:
            # 8XY6: Shifts VX right by one. VF is set to the value of 
            # the least significant bit of VX before the shift.
            self.reg[0xf] = self.reg[vx] & 0x1
            self.reg[vx] >>= 1
        elif subop == 7:
            # 8XY7: Sets VX to VY minus VX. VF is set to 0 when there's 
            # a borrow, and 1 when there isn't.
            if self.reg[vy] >= slef.reg[vx]:
                self.reg[vx] = self.reg[vy] - self.reg[vx]
                self.reg[0xf] = 1
            else:
                self.reg[vx] = self.reg[vy] + 0x100 - self.reg[vx]
                self.reg[0xf] = 0
        elif subop == 15:
            # 8XYE: Shifts VX left by one. VF is set to the value of 
            # the most significant bit of VX before the shift.
            self.reg[0xf] = (self.reg[vx] >> 7) & 0x1
            self.reg[vx] <<= 1
        else:
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def op_9(self):
        if self.opcode & 0xf == 0:
            # 9XY0: Skips the next instruction if VX doesn't equal VY.
            vx = (self.opcode & 0x0f00) >> 8
            vy = (self.opcode & 0x00f0) >> 4
            if self.reg[vx] != self.reg[vy]:
                self.pc += 2
        else:
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def op_A(self):
        # ANNN: Sets I to the address NNN.
        self.I = self.opcode & 0xfff

    def op_B(self):
        # BNNN: Jumps to the address NNN plus V0.
        self.pc = (self.opcode & 0xfff) + self.reg[0]

    def op_C(self):
        # CXNN: Sets VX to the result of a bitwise and operation on a random
        # number and NN.
        vx = (self.opcode & 0x0f00) >> 8
        nn = self.opcode & 0x00ff
        self.reg[vx] = int(random.random() * 255) & nn

    def op_D(self):
        # DxYN: Sprites stored in memory at location in index register (I), 8bits wide. 
        # Wraps around the screen. If when drawn, clears a pixel, register VF is set 
        # to 1 otherwise it is zero. All drawing is XOR drawing (i.e. it toggles the 
        # screen pixels). Sprites are drawn starting at position VX, VY. N is the number 
        # of 8bit rows that need to be drawn. If N is greater than 1, second line continues 
        # at position VX, VY+1, and so on.
        #print "op_D: {:04x}".format(self.opcode)
        #print "Index: ", self.I
        height = self.opcode & 0x000f
        vx = (self.opcode & 0x0f00) >> 8
        vy = (self.opcode & 0x00f0) >> 4
        x = self.reg[vx]
        y = self.reg[vy]
        # no collision yet
        self.reg[0xf] = 0
        for i in range(0, height):
            ymod = (y + i) % 32
            byte = self.memory[self.I + i]
            for j in range(0, 8):
                xmod = (x + j) % 64
                #if (y+i) >= 0 and (y+i) < 32 and (x+j) >= 0 and (x+j) < 64:
                bit = (byte >> (7 - j)) & 0x1
                if bit == 1:
                    self.pixels[ymod][xmod] ^= 1 
                    self.draw_pixel(self.pixels[ymod][xmod], xmod, ymod)
                    if self.pixels[ymod][xmod] == 0x0:
                        # collision detected
                        self.reg[0xf] = 1
        pygame.display.flip()

    def op_E(self):
        subop = self.opcode & 0xff
        vx = (self.opcode & 0x0f00) >> 8
        key = self.reg[vx]
        if subop == 0x9e:
            # EX9E: Skips the next instruction if the key stored in VX is pressed.
            if self.key[key] == 1:
                self.pc += 2
        elif subop == 0xa1:
            # EXA1: Skips the next instruction if the key stored in VX isn't pressed.
            if self.key[key] == 0:
                self.pc += 2
        else:
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def op_F(self):
        subop = self.opcode & 0xff
        vx = (self.opcode & 0x0f00) >> 8
        if subop == 0x07:
            # FX07: Sets VX to the value of the delay timer.
            self.reg[vx] = self.delay_timer
        elif subop == 0x0a:
            # FX0A: A key press is awaited, and then stored in VX.
            done = False
            while not done:
                for event in pygame.event.get():
                    if event.type == KEYDOWN:
                        if event.key in key_map:
                            done = True
                            self.reg[vx] = key_map.index(event.key)
        elif subop == 0x15:
            # FX15: Sets the delay timer to VX.
            self.delay_timer = self.reg[vx]
        elif subop == 0x18:
            # FX18: Sets the sound timer to VX.
            self.sound_timer = self.reg[vx]
        elif subop == 0x1e:
            # FX1E: Adds VX to I. VF is set to 1 when range overflow (I+VX>0xFFF), and 0 when there isn't. 
            # This is undocumented feature of the CHIP-8 and used by Spacefight 2091! game.
            self.I += self.reg[vx]
            if self.I > 0xfff:
                self.I -= 0x1000
                self.reg[0xf] = 1
            else:
                self.reg[0xf] = 0
        elif subop == 0x29:
            # FX29: Sets I to the location of the sprite for the character in VX. 
            # Characters 0-F (in hexadecimal) are represented by a 4x5 font.
            self.I = self.reg[vx] * 5
        elif subop == 0x33:
            # Stores the Binary-coded decimal representation of VX, with the most 
            # significant of three digits at the address in I, the middle digit 
            # at I plus 1, and the least significant digit at I plus 2. (In other 
            # words, take the decimal representation of VX, place the hundreds digit
            # in memory at location in I, the tens digit at location I+1, and the 
            # ones digit at location I+2.)
            temp = self.reg[vx]
            self.memory[self.I] = temp / 100
            self.memory[self.I+1] = (temp / 10) % 10
            self.memory[self.I+2] = temp % 10
        elif subop == 0x55:
            # FX55: Stores V0 to VX in memory starting at address I.
            for i in range(0, vx+1):
                self.memory[self.I+i] = self.reg[i]
        elif subop == 0x65:
            # FX65: Fills V0 to VX with values from memory starting at address I.
            for i in range(0, vx+1):
                self.reg[i] = self.memory[self.I+i]
        else:
            print "error: unsupported opcode: {:04x}".format(self.opcode)

    def run(self):
        done = True
        while done:
            # handle event
            for event in pygame.event.get():
                if event.type == QUIT:
                    done = False
                    break
                elif event.type == KEYDOWN:
                    if event.key in key_map:
                        print "key down: ", key_map.index(event.key)
                        self.key[key_map.index(event.key)] = 1
                elif event.type == KEYUP:
                    if event.key in key_map:
                        print "key up: ", key_map.index(event.key)
                        self.key[key_map.index(event.key)] = 0
            # fecth code: Chip-8 are all two bytes long and stored big-endian
            self.opcode = (self.memory[self.pc] << 8) + self.memory[self.pc + 1]
            #print "0x{:04x}".format(self.opcode)
            # update program counter
            self.pc += 2
            opc = self.opcode >> 12
            # decode opcode
            func_str = "op_" + "{:X}".format(opc)
            # excute
            getattr(self, func_str)()
            # update timer
            if self.delay_timer > 0:
                self.delay_timer -= 1
            if self.sound_timer > 0:
                self.sound_timer -= 1
            self.clock.tick(600)

def test():
    """Chip8 test"""
    chip8 = Chip8('TANK')
    #chip8 = Chip8('IBM')
    #while True:
    #    pass
    #chip8.dump_memory()
    chip8.run()

if __name__=='__main__':
    test()
