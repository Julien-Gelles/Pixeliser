import sys, time, argparse, ast
from PIL import Image, ImageDraw, ImageFont
from tkinter import filedialog

color_dict = {}

def rgb_to_lab(rgb):
    r, g, b = rgb
    r /= 255.0
    g /= 255.0
    b /= 255.0

    r = (r / 12.92) if (r <= 0.04045) else ((r + 0.055) / 1.055) ** 2.4
    g = (g / 12.92) if (g <= 0.04045) else ((g + 0.055) / 1.055) ** 2.4
    b = (b / 12.92) if (b <= 0.04045) else ((b + 0.055) / 1.055) ** 2.4

    r *= 100.0
    g *= 100.0
    b *= 100.0

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    x /= 95.047
    y /= 100.000
    z /= 108.883

    x = (x ** (1.0 / 3.0)) if (x > 0.008856) else (903.3 * x + 16.0) / 116.0
    y = (y ** (1.0 / 3.0)) if (y > 0.008856) else (903.3 * y + 16.0) / 116.0
    z = (z ** (1.0 / 3.0)) if (z > 0.008856) else (903.3 * z + 16.0) / 116.0

    l = max(0.0, 116.0 * y - 16.0)
    a = (x - y) * 500.0
    b = (y - z) * 200.0

    return l, a, b

def color_distance(color1, color2):
    l1, a1, b1 = color1
    l2, a2, b2 = color2
    delta_l = l2 - l1
    delta_a = a2 - a1
    delta_b = b2 - b1

    distance = (delta_l ** 2 + delta_a ** 2 + delta_b ** 2) ** 0.5
    return distance

#------------------------------------------------

def getCloserColor(target_color, color_list):
    lab_target_color = rgb_to_lab(target_color)
    lab_color_list = [rgb_to_lab(color) for color in color_list]

    min_distance = float('inf')
    closest_color_index = -1

    for i, lab_color in enumerate(lab_color_list):
        distance = color_distance(lab_target_color, lab_color)
        if distance < min_distance:
            min_distance = distance
            closest_color_index = i

    return color_list[closest_color_index]

def getCloserColor2(rgb_color, color_list):
    min_distance = float('inf')
    closest_color = None

    for color in color_list:
        distance = sum((a - b) ** 2 for a, b in zip(rgb_color, color))
        if distance < min_distance:
            min_distance = distance
            closest_color = color

    return closest_color

#------------------------------------------------

def recolorImage(image, color_list, version):
    new_im = Image.new("RGB", image.size)
    for x in range(image.width):
        for y in range(image.height):
            pixel_values = image.getpixel((x, y))
            (r, g, b) = pixel_values[:3]
            if ((r,g,b) in color_dict):
                color = color_dict[(r,g,b)]
            else:
                match version:
                    case 1:
                        color = getCloserColor((r, g, b), color_list)
                    case 2:
                        color = getCloserColor2((r, g, b), color_list)
                color_dict[(r,g,b)] = color
            new_im.putpixel((x,y), color)
    return new_im

def pixeliseImage(pixelDegree, image, color_list, version, quick):
    if quick:
        small_im = image.resize((int(image.width/pixelDegree),int(image.height/pixelDegree)), resample=Image.Resampling.NEAREST)
        return recolorImage(small_im, color_list, version).resize(image.size, Image.Resampling.NEAREST)
    else:
        recolor_im = recolorImage(image, color_list, version)
        small_im = recolor_im.resize((int(image.width/pixelDegree),int(image.height/pixelDegree)), resample=Image.Resampling.NEAREST)
        return small_im.resize(image.size, Image.Resampling.NEAREST)

#------------------------------------------------

def generate_symbols(color_list):
    n = len(color_list)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    symbols = []

    if n <= 26:
        return list(alphabet[:n])

    suffix = 0
    while len(symbols) < n:
        for letter in alphabet:
            symbols.append(f"{letter}{suffix}")
            if len(symbols) >= n:
                return symbols
        suffix += 1

def create_legend_image(pixelized_img, color_list, pixel_size, highlight_symbol=None, info_text=None):
    symbols = generate_symbols(color_list)
    color_to_symbol = {tuple(c): symbols[i] for i, c in enumerate(color_list)}

    legend_img = Image.new("RGB", pixelized_img.size, (255, 255, 255))
    draw = ImageDraw.Draw(legend_img)

    try:
        font = ImageFont.truetype("arial.ttf", pixel_size // 2)
    except:
        font = ImageFont.load_default()

    for y in range(0, pixelized_img.height, pixel_size):
        for x in range(0, pixelized_img.width, pixel_size):
            color = pixelized_img.getpixel((x, y))
            symbol = color_to_symbol.get(tuple(color), "?")

            if highlight_symbol is not None and symbol == highlight_symbol:
                draw.rectangle([x, y, x + pixel_size, y + pixel_size], fill=tuple(color), outline=(0, 0, 0), width=2)
            else:
                bbox = draw.textbbox((0, 0), symbol, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                draw.text(
                    (x + (pixel_size - w) / 2, y + (pixel_size - h) / 2),
                    symbol,
                    fill=(0, 0, 0),
                    font=font
                )
                draw.rectangle([x, y, x + pixel_size, y + pixel_size], outline=(0, 0, 0), width=1)

    if info_text:
        info_height = pixel_size
        rect_y0 = legend_img.height - info_height
        draw.rectangle([0, rect_y0, legend_img.width, legend_img.height], fill=(255, 255, 255))
        try:
            font_info = ImageFont.truetype("arial.ttf", info_height - 4)
        except:
            font_info = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), info_text, font=font_info)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_text = (legend_img.width - w) / 2
        y_text = rect_y0 + (info_height - h) / 2
        draw.text((x_text, y_text), info_text, fill=(0, 0, 0), font=font_info)

    return legend_img


#------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file')
    parser.add_argument('-p', '--pixels')
    parser.add_argument('-c', '--color_list')
    parser.add_argument('-v', '--version')
    parser.add_argument('-q', '--quick', action='store_true')
    parser.add_argument('-i', '--initial', action='store_true')
    parser.add_argument('-s', '--steps', action='store_true')
    parser.add_argument('-l', '--legend', nargs='?', const=True, default=False)
    args = parser.parse_args()

    file_arg = args.file
    pixels_arg = args.pixels
    color_list_arg = args.color_list
    version_arg = args.version
    quick_arg = args.quick
    initial_arg = args.initial
    legend_arg = args.legend
    step_arg = args.steps

    if file_arg == None:
        file_types = [("Image files", "*.png"),("Image files", "*.jpg"),("Image files", "*.jpeg"),("Image files", "*.bmp"),("Image files", "*.ppm"),("Image files", "*.pgm")]
        file = filedialog.askopenfilename(filetypes=file_types)
        if (file == None or file == ()):
            sys.exit()
        file_arg = file
    if pixels_arg == None:
        pixels_arg = 16
    if color_list_arg == None:
        color_list_arg = [
            (73,41,20),
            (122,63,23),
            (188,26,26),
            (202,84,29),
            (255,169,40),
            (255,235,53),
            (131,188,26),
            (30,167,17),
            (9,104,0),
            (1,177,133),
            (120,212,255),
            (56,97,235),
            (1,37,156),
            (32,0,45),
            (142,26,188),
            (188,26,166),
            (255,168,243),
            (246,225,207),
            (250,250,250),
            (14,13,13)
        ]
    else:
        color_list_arg = ast.literal_eval(color_list_arg)
    if version_arg == None:
        version_arg = 1

    try:
        print("Program runnin..")
        start_time = time.time()
        im = Image.open(file_arg)
        final_im = pixeliseImage(int(pixels_arg), im, color_list_arg, int(version_arg), quick_arg)
        if initial_arg:
            im.show()
        
        if legend_arg:
            block_size = int(im.width / (im.width // int(pixels_arg)))
            highlight_symbol = legend_arg if isinstance(legend_arg, str) else None
            legend_img = create_legend_image(final_im, color_list_arg, block_size, highlight_symbol)
            legend_img.show()

        final_im.show()

        end_time = time.time()
        duration = round(end_time - start_time,2)
        if duration > 1: print("Done in", round(end_time - start_time,2) , "seconds.")
        else: print("Done in", round(end_time - start_time,2) , "second.")

        if steps_arg := args.steps:
            block_size = int(im.width / (im.width // int(pixels_arg)))
            symbols = generate_symbols(color_list_arg)
            color_to_symbol = {tuple(c): symbols[i] for i, c in enumerate(color_list_arg)}

            pixels_present = set()
            for x in range(final_im.width):
                for y in range(final_im.height):
                    pixels_present.add(final_im.getpixel((x,y)))

            colors_present = [c for c in color_list_arg if c in pixels_present]

            for color in colors_present:
                symbol = color_to_symbol[tuple(color)]
                info_text = f"Color RGB: {color} | Symbol: {symbol}"
                legend_img = create_legend_image(final_im, color_list_arg, block_size, highlight_symbol=symbol, info_text=info_text)
                legend_img.show()
                print(f"Displayed color {color} with symbol '{symbol}'. Close image to continue...")
                input("Press Enter after closing the image...")
        
    except Exception as e:
        print("Bad Input :c\n",e) 