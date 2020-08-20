import csv
import os

from PIL import Image, ImageDraw, ImageFont
from avalon import harmony

import pype.hosts.harmony


class ExtractPalette(pype.api.Extractor):
    """Extract palette."""

    label = "Extract Palette"
    hosts = ["harmony"]
    families = ["palette"]

    def process(self, instance):
        func = """function func(args)
        {
            var palette_list = PaletteObjectManager.getScenePaletteList();
            var palette = palette_list.getPaletteById(args[0]);
            var palette_name = palette.getName()
            return [palette_name, (palette.getPath() + "/" + palette.getName() + ".plt")];
        }
        func
        """

        result = harmony.send(
            {"function": func, "args": [instance.data["id"]]}
        )["result"]
        palette_name = result[0]
        palette_file = result[1]

        representation = {
            "name": "plt",
            "ext": "plt",
            "files": os.path.basename(palette_file),
            "stagingDir": os.path.dirname(palette_file)
        }

        tmp_thumb_path = os.path.join(os.path.dirname(palette_file),
                                      os.path.basename(palette_file)
                                      .split(".plt")[0] + "_swatches.png"
                                      )
        palette_version = str(instance.data.get("version")).zfill(3)

        thumbnail_path = self.create_palette_thumbnail(palette_name,
                                                       palette_version,
                                                       palette_file,
                                                       tmp_thumb_path)
        thumbnail = {
            "name": "thumbnail",
            "ext": "png",
            "files": os.path.basename(thumbnail_path),
            "stagingDir": os.path.dirname(thumbnail_path),
            "tags": ["thumbnail"]
        }

        instance.data["representations"] = [representation, thumbnail]

    def create_palette_thumbnail(self,
                                 palette_name,
                                 palette_version,
                                 palette_path,
                                 dst_path):
        colors = {}

        with open(palette_path, newline='') as plt:
            plt_parser = csv.reader(plt, delimiter=" ")
            for i, line in enumerate(plt_parser):
                if i == 0: continue
                while ("" in line): line.remove("")
                print(line)
                color_name = line[1].strip('"')
                colors[color_name] = {"type": line[0],
                                      "uuid": line[2],
                                      "rgba": (int(line[3]),
                                               int(line[4]),
                                               int(line[5]),
                                               int(line[6])),
                                      }
            plt.close()

        img_pad_top = 80
        label_pad_name = 30
        label_pad_rgb = 580
        swatch_pad_left = 300
        swatch_pad_top = 10
        swatch_w = 120
        swatch_h = 50

        image_w = 800
        image_h = (img_pad_top +
                   (len(colors.keys()) *
                    swatch_h) +
                   (swatch_pad_top *
                    len(colors.keys()))
                   )

        img = Image.new("RGBA", (image_w, image_h), "white")

        # For bg of colors with alpha, create checkerboard image
        checkers = Image.new("RGB", (swatch_w, swatch_h))
        pixels = checkers.load()

        # Make pixels white where (row+col) is odd
        for i in range(swatch_w):
            for j in range(swatch_h):
                if (i + j) % 2:
                    pixels[i, j] = (255, 255, 255)

        draw = ImageDraw.Draw(img)
        title_font = ImageFont.truetype("arial.ttf", 28)
        label_font = ImageFont.truetype("arial.ttf", 20)


        draw.text((label_pad_name, 20),
                  "{} (v{})".format(palette_name, palette_version),
                  "black",
                  font=title_font)

        for i, name in enumerate(colors):
            rgba = colors[name]["rgba"]
            # @TODO: Fix this so alpha colors are displayed with checkboard
            # if not rgba[3] == "255":
            #     img.paste(checkers,
            #               (swatch_pad_left,
            #                img_pad_top + swatch_pad_top + (i * swatch_h))
            #               )
            #
            #     half_y = (img_pad_top + swatch_pad_top + (i * swatch_h))/2
            #
            #     draw.rectangle((
            #         swatch_pad_left,  # upper left x
            #         img_pad_top + swatch_pad_top + (i * swatch_h),  # upper left y
            #         swatch_pad_left + (swatch_w * 2),  # lower right x
            #         half_y),  # lower right y
            #         fill=rgba[:-1], outline=(0, 0, 0), width=2)
            #     draw.rectangle((
            #         swatch_pad_left,  # upper left x
            #         half_y,  # upper left y
            #         swatch_pad_left + (swatch_w * 2),  # lower right x
            #         img_pad_top + swatch_h + (i * swatch_h)),  # lower right y
            #         fill=rgba, outline=(0, 0, 0), width=2)
            # else:

            draw.rectangle((
                swatch_pad_left,  # upper left x
                img_pad_top + swatch_pad_top + (i * swatch_h),  # upper left y
                swatch_pad_left + (swatch_w * 2),  # lower right x
                img_pad_top + swatch_h + (i * swatch_h)),  # lower right y
                fill=rgba, outline=(0, 0, 0), width=2)

            draw.text((label_pad_name, img_pad_top + (i * swatch_h) + swatch_pad_top + (swatch_h / 4)),
                      name,
                      "black",
                      font=label_font)

            draw.text((label_pad_rgb, img_pad_top + (i * swatch_h) + swatch_pad_top + (swatch_h / 4)),
                      str(rgba),
                      "black",
                      font=label_font)

        draw = ImageDraw.Draw(img)

        img.save(dst_path)
        return dst_path
