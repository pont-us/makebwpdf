makebwpdf
---------

Convert a series of image files to a multi-page bilevel (i.e. black and
white) PDF.

Requires: econvert (from https://exactcode.com/opensource/exactimage/ ),
tiffcp, and tiff2pdf.

By Pontus Lurcock, 2017 (pont -at- talvi.net).
Released into the public domain.

    usage: makebwpdf.py [-h] [--brightness BRIGHTNESS] [--output OUTPUT]
                        input_file [input_file ...]
    
    positional arguments:
      input_file            input filename
    
    optional arguments:
      -h, --help            show this help message and exit
      --brightness BRIGHTNESS, -b BRIGHTNESS
      --output OUTPUT, -o OUTPUT

If no output file is specified, the PDF is written to the standard
output.

If no brightness is specified, a brightness of 0 is used.
