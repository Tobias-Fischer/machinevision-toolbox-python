import cv2 as cv
from spatialmath import base
from ansitable import ANSITable, Column
from machinevisiontoolbox.base import color_bgr
import matplotlib.pyplot as plt
import numpy as np


def draw_box(image, 
        bbox=None, bl=None, tl=None, br=None, tr=None, wh=None, centre=None,
        color=None, fillcolor=None, alpha=None, thickness=1, **kwargs):
    """
    Draw a box in an image using OpenCV

    :param image: image to draw into
    :type image: ndarray(h,w) or ndarray(h,w,nc)
    :param bbox: bounding box matrix, defaults to None
    :type bbox: ndarray(2,2), optional
    :param bl: bottom-left corner, defaults to None
    :type bl: array_like(2), optional
    :param tl: top-left corner, defaults to None
    :type tl: [array_like(2), optional
    :param br: bottom-right corner, defaults to None
    :type br: array_like(2), optional
    :param tr: top-right corner, defaults to None
    :type tr: array_like(2), optional
    :param wh: width and height, defaults to None
    :type wh: array_like(2), optional
    :param centre: [description], defaults to None
    :type centre: array_like(2), optional
    :param color: box outline color
    :type color: array_like(3) or str
    :param fillcolor: box fill color
    :type fillcolor: array_like(3) or str
    :param thickness: [description], defaults to 1
    :type thickness: int, optional
    :return: bottom-left and top right-corners
    :rtype: [type]

    Draws a box into the specified image using OpenCV.  The input ``image``
    is modified.

    The box can be specified in many ways:

    - bounding box which is a 2x2 matrix [xmin, xmax; ymin, ymax]
    - centre and width+height
    - bottom-left and top-right corners
    - bottom-left corner and width+height
    - top-right corner and width+height
    - top-left corner and width+height

    where bottom-left is (xmin, ymin), top-left is (xmax, ymax)
    """

    if not isinstance(color, int) and len(image.shape) == 2:
        raise TypeError("can't draw color into a greyscale image")

    if bbox is not None:
        bl = tuple(bbox[:,0])
        tr = tuple(bbox[:,1])
    elif bl is not None and tl is None and tr is None and wh is not None and centre is None:
        # bl + wh
        bl = tuple(bl)
        w, h = wh
        tr = (bl[0] + w, bl[1] + h)
    elif bl is not None and tl is None and tr is not None and wh is None and centre is None:
        # bl + tr
        bl = tuple(bl)
        tr = tuple(tr)
    elif bl is None and tl is None and tr is None and wh is not None and centre is not None:
        # centre + wh
        w, h = wh
        bl = (centre[0] - w / 2, centre[1] - h / 2)
        tr = (centre[0] + w / 2, centre[1] + h / 2)
    elif bl is None and tl is None and tr is not None and wh is not None and centre is None:
        # tr + wh
        tr = tuple(tr)
        w, h = wh
        bl = (tr[0] - w, tr[1] - h)
    elif bl is None and tl is not None and tr is None and wh is not None and centre is None:
        # tl + wh
        w, h = wh
        bl = (tl[0], tl[1] - h)
        tr = (tl[0] + w, tl[1])

    if fillcolor is not None:
        color = fillcolor
        thickness = -1
    if isinstance(color, str):
        color = color_bgr(color)
    
    if color is not None and len(color) == 3:
        color = color[::-1]
    bl = tuple([int(x) for x in bl])
    tr = tuple([int(x) for x in tr])
    cv.rectangle(image, bl, tr, color, thickness)

    return bl, tr


def plot_labelbox(text, textcolor=None, **kwargs):
    """
    Plot a labelled box using matplotlib

    :param text: text label
    :type text: str
    :param textcolor: text color, defaults to None
    :type textcolor: str or array_like(3), optional

    The position of the box is specified using the same arguments as for
    ``plot_box``.

    The label font is specified using the same arguments as for ``plot_text``.

    :seealso: :func:`plot_box`, :func:`plot_text`
    """

    rect = plot_box(**kwargs)

    bbox = rect.get_bbox()

    plot_text((bbox.xmin, bbox.ymin), text, color=textcolor, verticalalignment='bottom', 
        bbox=dict(facecolor=kwargs['color'], linewidth=0, edgecolor=None))


def draw_labelbox(image, text, textcolor='black', 
    font=cv.FONT_HERSHEY_SIMPLEX, fontsize=0.9, fontthickness=2, **kwargs):
    """
    Draw a labelled box in the image using OpenCV

    :param text: text label
    :type text: str
    :param textcolor: text color, defaults to black
    :type textcolor: str or array_like(3), optional
    :param font: OpenCV font, defaults to cv.FONT_HERSHEY_SIMPLEX
    :type font: str, optional
    :param fontsize: OpenCV font scale, defaults to 0.3
    :type fontsize: float, optional
    :param fontthickness: font thickness in pixels, defaults to 2
    :type fontthickness: int, optional

    The position of the box is specified using the same arguments as for
    ``draw_box``.

    The label font is specified using the same arguments as for ``draw_text``.

    :seealso: :func:`draw_box`, :func:`draw_text`
    """

    if not isinstance(color, int) and len(image.shape) == 2:
        raise TypeError("can't draw color into a greyscale image")

    # get size of text:  ((w,h), baseline)
    twh = cv.getTextSize(text, font, fontsize, fontthickness)

    # draw the box
    bl, tr = draw_box(image, **kwargs)

    # a bit of margin, 1/2 the text height
    h = round(twh[0][1] / 2)
    h2 = round(twh[0][1] / 4)

    # draw background of the label
    draw_box(image, tl=bl, wh=(twh[0][0] + h, twh[0][1] + h), fillcolor=kwargs['color'])

    # draw the text over the background
    draw_text(image, (bl[0] + h2, bl[1] - h2), text, color=textcolor,
        font=font, fontsize=fontsize, fontthickness=fontthickness)

def draw_text(image, pos, text=None, color=None, font=cv.FONT_HERSHEY_SIMPLEX, fontsize=0.3, fontthickness=2):
    """
    Draw text in image using OpenCV

    :param image: image to draw into
    :type image: ndarray(h,w) or ndarray(h,w,nc)
    :param pos: position of text
    :type pos: array_like(2)
    :param text: text
    :type text: str
    :param color: color of text
    :type color: scalar, array_like(3), str
    :param font: OpenCV font, defaults to cv.FONT_HERSHEY_SIMPLEX
    :type font: str, optional
    :param fontsize: OpenCV font scale, defaults to 0.3
    :type fontsize: float, optional
    :param fontthickness: font thickness in pixels, defaults to 2
    :type fontthickness: int, optional

    The position corresponds to the bottom-left corner of the text box as seen
    in the image.
    """
    if not isinstance(color, int) and len(image.shape) == 2:
        raise TypeError("can't draw color into a greyscale image")

    if isinstance(color, str):
        color = color_bgr(color)

    cv.putText(image, text, pos, font, fontsize, color, fontthickness)

def draw_point(image, pos, marker='+', text=None, color=None, font=cv.FONT_HERSHEY_SIMPLEX, fontsize=0.3, fontthickness=2):
    """
    Draw marker in image using OpenCV

    :param image: image to draw into
    :type image: ndarray(h,w) or ndarray(h,w,nc)
    :param pos: position of marker
    :type pos: array_like(2), ndarray(2,n), list of 2-tuples
    :param marker: marker character, defaults to '+'
    :type marker: str, optional
    :param text: text label, defaults to None
    :type text: str, optional
    :param color: text color, defaults to None
    :type color: str or array_like(3), optional
    :param font: OpenCV font, defaults to cv.FONT_HERSHEY_SIMPLEX
    :type font: str, optional
    :param fontsize: OpenCV font scale, defaults to 0.3
    :type fontsize: float, optional
    :param fontthickness: font thickness in pixels, defaults to 2
    :type fontthickness: int, optional

    The text label is placed to the right of the marker, and vertically centred.
    The color of the marker can be different to the color of the text, the
    marker color is specified by a single letter in the marker string.

    Multiple points can be marked if ``pos`` is a 2xn array or a list of 
    coordinate pairs.  If a label is provided every point will have the same
    label. However, the text is processed with ``format`` and is provided with
    a single argument, the point index (starting at zero).
    """

    if not isinstance(color, int) and len(image.shape) == 2:
        raise TypeError("can't draw color into a greyscale image")
    
    if isinstance(pos, np.ndarray) and pos.shape[0] == 2:
        x = pos[0,:]
        y = pos[1,:]
    elif isinstance(pos, (tuple, list)):
        if base.islistof(pos, (tuple, list)):
            x = [z[0] for z in pos]
            y = [z[1] for z in pos]
        else:
            x = pos[0]
            y = pos[1]

    if isinstance(color, str):
        color = color_bgr(color)

    for i, xy in enumerate(zip(x, y)):
        s = marker
        if text:
            s += ' ' + text.format(i)
        cv.putText(image, s, xy, font, fontsize, color, fontthickness)

# def plot_histogram(c, n, clip=False, ax=None, block=False, xlabel=None, ylabel=None, grid=False, **kwargs):
#     if ax is None:
#         plt.figure()
#         ax = plt.gca()

#     # n = hist.h  # number of pixels per class
#     # c = hist.x  # class value

#     if clip:
#         nz, _ = np.where(n > 0)
#         start = nz[0]
#         end = nz[-1] + 1
#         n = n[start:end]
#         c = c[start:end]

#     ax.bar(c, n, **kwargs)
#     if xlabel is not None:
#         ax.set_xlabel(xlabel)
#     if ylabel is not None:
#         ax.set_ylabel(ylabel)
#     ax.grid(grid)

    # plt.show(block=block)

if __name__ == "__main__":

    # from machinevisiontoolbox import iread, idisp

    # im, file = iread('flowers1.png')
    # idisp(im, darken=2)

    # plot_box(centre=(300,200), wh=(40,40), fillcolor='red', alpha=0.5)

    # plot_point([(200,200), (300, 300), (400,400)], marker='r*', color='blue', text="bob {}")

    # plot_labelbox("hello", color='red', textcolor='white', centre=(300,300), wh=(60,40))
    # plt.show()

    import numpy as np
    from machinevisiontoolbox import idisp, iread, Image

    im = np.zeros((100,100,3), 'uint8')
    # im, file = iread('flowers1.png')

    # draw_box(im, color=(255,0,0), centre=(50,50), wh=(20,20))

    # draw_point(im, [(200,200), (300, 300), (400,400)], color='blue')

    # draw_labelbox(im, "box", thickness=3, centre=(100,100), wh=(100,30), color='red', textcolor='white')
    idisp(im)

    x = np.random.randint(0, 100, size=(10,))
    y = np.random.randint(0, 100, size=(10,))

    plot_point((x,y), 'w+')
    plt.draw()
    plt.show(block=True)

    im = Image('penguins.png')
    h = im.hist()
    