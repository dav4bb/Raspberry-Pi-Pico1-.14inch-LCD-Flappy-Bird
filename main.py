from machine import Pin, SPI
import framebuf
import time
import random

# --- ST7789 EKRAN SÜRÜCÜSÜ ---
class ST7789(framebuf.FrameBuffer):
    def __init__(self, spi, width, height, dc, cs, rst, bl):
        self.spi = spi
        self.width = width
        self.height = height
        self.dc = dc
        self.cs = cs
        self.rst = rst
        self.bl = bl
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()

    def write_cmd(self, cmd):
        self.dc(0); self.cs(0); self.spi.write(bytearray([cmd])); self.cs(1)

    def write_data(self, buf):
        self.dc(1); self.cs(0); self.spi.write(bytearray([buf])); self.cs(1)

    def init_display(self):
        self.rst(1); time.sleep(0.01); self.rst(0); time.sleep(0.01); self.rst(1)
        self.bl(1)
        # Ekran başlatma ayarları
        for cmd, data in [(0x36, 0x70), (0x3A, 0x05), (0x21, None), (0x11, None), (0x29, None)]:
            self.write_cmd(cmd)
            if data is not None: self.write_data(data)

    def show(self):
        self.write_cmd(0x2A) 
        self.write_data(0x00); self.write_data(40)
        self.write_data(0x01); self.write_data(40 + 240 - 1)
        self.write_cmd(0x2B)
        self.write_data(0x00); self.write_data(53)
        self.write_data(0x00); self.write_data(53 + 135 - 1)
        self.write_cmd(0x2C)
        self.cs(0); self.dc(1); self.spi.write(self.buffer); self.cs(1)

# --- RENK TANIMLAMALARI ---
SKY_BLUE = 0x4D39; WHITE = 0xFFFF; YELLOW = 0xFFE0; GREEN = 0x07E0
BLACK = 0x0000; ORANGE = 0xFD20; D_GREEN = 0x03E0; BROWN = 0x9240

# --- DONANIM KURULUMU ---
spi = SPI(1, baudrate=40_000_000, sck=Pin(10), mosi=Pin(11))
lcd = ST7789(spi, 240, 135, dc=Pin(8, Pin.OUT), cs=Pin(9, Pin.OUT), rst=Pin(12, Pin.OUT), bl=Pin(13, Pin.OUT))

def get_hi():
    try:
        with open("hi.txt", "r") as f: return int(f.read())
    except: return 0

def set_hi(s):
    try:
        with open("hi.txt", "w") as f: f.write(str(s))
    except: pass

# --- ÇİZİM FONKSİYONLARI ---
def draw_bird(y, v, frame):
    bx = 35 
    tilt = 2 if v > 1 else (-1 if v < -1 else 0)
    
    # Gövde
    lcd.fill_rect(bx, y, 17, 12, YELLOW)
    lcd.rect(bx, y, 17, 12, BLACK)
    
    # Kanat (Animasyonlu)
    wing_pos = (frame // 4) % 2 
    lcd.fill_rect(bx-4, y+3+wing_pos, 8, 5, WHITE)
    lcd.rect(bx-4, y+3+wing_pos, 8, 5, BLACK)
    
    # Göz
    lcd.fill_rect(bx+10, y+1+tilt, 6, 5, WHITE)
    lcd.rect(bx+10, y+1+tilt, 6, 5, BLACK)
    lcd.pixel(bx+14, y+2+tilt, BLACK)
    
    # Gaga
    lcd.fill_rect(bx+15, y+6+tilt, 6, 4, ORANGE)
    lcd.rect(bx+15, y+6+tilt, 6, 4, BLACK)

def draw_pipes(px, ph, gap):
    # Üst Boru
    lcd.fill_rect(int(px), 0, 30, int(ph), GREEN)
    lcd.rect(int(px), 0, 30, int(ph), BLACK)
    lcd.fill_rect(int(px-2), int(ph-10), 34, 10, D_GREEN)
    lcd.rect(int(px-2), int(ph-10), 34, 10, BLACK)
    
    # Alt Boru
    lower_y = int(ph + gap)
    lcd.fill_rect(int(px), lower_y, 30, 135 - lower_y, GREEN)
    lcd.rect(int(px), lower_y, 30, 135 - lower_y, BLACK)
    lcd.fill_rect(int(px-2), lower_y, 34, 10, D_GREEN)
    lcd.rect(int(px-2), lower_y, 34, 10, BLACK)

# --- ANA OYUN DÖNGÜSÜ ---
def main():
    hi = get_hi()
    bird_y = 60
    bird_v = 0
    score = 0
    px = 240
    ph = random.randint(20, 65)
    gap = 52       # Boru boşluğu
    game_speed = 4 # Başlangıç hızı
    frame = 0
    
    btn = Pin(3, Pin.IN, Pin.PULL_UP)
    keyA = Pin(15, Pin.IN, Pin.PULL_UP)

    while True:
        # Zıplama kontrolü
        if btn.value() == 0 or keyA.value() == 0:
            bird_v = -3.8
            
        # Fizik
        bird_v += 0.32
        bird_y += int(bird_v)
        px -= game_speed
        frame += 1
        
        # Boru sıfırlama ve Skor
        if px < -35:
            px = 240
            ph = random.randint(20, 70)
            score += 1
            
            # HIZLANMA SİSTEMİ: Her 5 skorda bir hız 0.5 artar (Max 8)
            if score % 5 == 0 and game_speed < 8:
                game_speed += 0.5
            
            # Zorluk artışı: Boşluk daralır (Min 40)
            if gap > 40:
                gap -= 1

        # Çarpışma Kontrolü
        if bird_y < 0 or bird_y > 118: break
        if (px < 35 + 17 and px + 30 > 35):
            if (bird_y < ph or bird_y + 10 > ph + gap):
                break

        # Çizim
        lcd.fill(SKY_BLUE)
        lcd.fill_rect(0, 128, 240, 7, BROWN) # Yer
        
        draw_pipes(px, ph, gap)
        draw_bird(bird_y, bird_v, frame)
        
        # Bilgiler
        lcd.text("Score:{}".format(score), 5, 5, WHITE)
        lcd.text("Best:{}".format(hi), 5, 15, YELLOW)
        lcd.text("Speed:{:.1f}".format(game_speed), 5, 25, WHITE)
        
        lcd.show()
        time.sleep(0.01)

    # Oyun Bitti
    if score > hi: set_hi(score)
    lcd.fill(BLACK)
    lcd.text("GAME OVER!", 80, 50, WHITE)
    lcd.text("Score: {}".format(score), 85, 70, YELLOW)
    lcd.show()
    time.sleep(1.5)
    main()

if __name__ == "__main__":
    main()
