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
        palette_version = "001"

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
                                      "rgb": (int(line[3]),
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
        swatch_x = 120
        swatch_y = 50
        image_x = 800
        image_y = (img_pad_top +
                   (len(colors.keys()) *
                    swatch_y) +
                   (swatch_pad_top *
                    len(colors.keys()))
                   )

        img = Image.new("RGBA", (image_x, image_y), "white")

        draw = ImageDraw.Draw(img)
        title_font = ImageFont.truetype("arial.ttf", 28)
        label_font = ImageFont.truetype("arial.ttf", 20)

        draw.text((label_pad_name, 20),
                  "{} (v{})".format(palette_name, palette_version),
                  "black",
                  font=title_font)

        for i, name in enumerate(colors):
            draw.rectangle((
                swatch_pad_left,  # upper left x
                img_pad_top + swatch_pad_top + (i * swatch_y),  # upper left y
                swatch_pad_left + (swatch_x * 2),  # lower right x
                img_pad_top + swatch_y + (i * swatch_y)),  # lower right y
                fill=colors[name]["rgb"], outline=(0, 0, 0), width=2)

            draw.text((label_pad_name, img_pad_top + (i * swatch_y) + swatch_pad_top + (swatch_y / 4)),
                      name,
                      "black",
                      font=label_font)
            draw.text((label_pad_rgb, img_pad_top + (i * swatch_y) + swatch_pad_top + (swatch_y / 4)),
                      str(colors[name]["rgb"]),
                      "black",
                      font=label_font)

        draw = ImageDraw.Draw(img)

        img.save(dst_path)
        return dst_path
