"""

vcat
grid(shape=(), list or *pos)


reduce(factor, width, height)
warp
affinemap

pad(halign="<^>", valign="^v-", align="<|>v^-, width=, height=)

samesize by scaling and padding
hcat
scale(factor, width, height)
rotate
"""

import numpy as np
import scipy as sp
import cv2 as cv
from spatialmath import base as smb
from machinevisiontoolbox.base import meshgrid, idisp

class ImageReshapeMixin:

    def trim(self, left=0, right=0, top=0, bottom=0):
        image = self.A
        y = slice(top, self.height-bottom)
        x = slice(left, self.width - right)
        if self.iscolor:
            image = image[y, x, :]
        else:
            image = image[y, x]
        
        return self.__class__(image, colororder=self.colororder)

    @classmethod
    def hcat(cls, *pos, pad=0):

        if isinstance(pos[0], (tuple, list)):
            images = pos[0]
        else:
            images = pos
        
        height = max([image.height for image in images])

        combo = np.empty(shape=(height,0))

        u = []
        for image in images:
            if image.height < height:
                image = np.pad(image.image, ((0,height-image.height),(0,0)), constant_values=(pad,0))
            else:
                image = image.image
            u.append(combo.shape[1])
            combo = np.hstack((combo, image))
        
        return cls(combo), u

    @classmethod
    def Tile(cls, tiles, columns=4, sep=2, bgcolor=0):
        # exemplars, shape=(-1, columns), **kwargs)

        # TODO tile a sequence into specified shape

        shape = tiles[0].shape
        colororder = tiles[0].colororder
        for tile in tiles[1:]:
            if tile.shape != shape:
                raise ValueError('all tiles must be same size')
            if tile.dtype != tiles[0].dtype:
                raise ValueError('all tiles must have same dtype')

        nrows = int(np.ceil(len(tiles) / columns))
        canvas = cls.Constant(
                    columns * shape[1] + (columns + 1) * sep,
                    nrows * shape[0] + (nrows + 1) * sep,
                    bgcolor,
                    dtype=tiles[0].dtype)
        if len(shape) == 3:
            canvas = canvas.colorize(colororder=colororder)

        v = sep
        while len(tiles) > 0:
            u = sep
            for c in range(columns):
                try:
                    im = tiles.pop(0)
                except IndexError:
                    break
                
                canvas.paste(im, (u, v), 'set', 'topleft')
                u += shape[1] + sep
            v += shape[0] + sep


        return canvas

    def pad(self, left=0, right=0, top=0, bottom=0, value=0):

        pw = ((top,bottom),(left,right))
        const = (value, value)

        return self.__class__(np.pad(self.image, pw, constant_values=const))


    def roi(self, reg=None, wh=None):
        """
        Extract region of interest

        :param reg: region
        :type reg: numpy array
        :param wh: width and/or height
        :type wh: 2-element vector of integers, or single integer
        :return: Image with roi as image
        :rtype: Image instance

        - ``IM.roi(rect)`` is a subimage of the image described by the
          rectangle ``rect=[umin, umax; vmin, vmax]``. The function returns the
          top, left, bottom and top coordinates of the selected region of
          interest, as vectors.

        - ``IM.roi(reg, wh)`` as above but the region is centered at
          ``reg=(U,V)`` and has a size ``wh``.  If ``wh`` is scalar then
          ``W=H=S`` otherwise ``S=(W,H)``.
        """

        # interpret reg
        if reg is not None and wh is not None:
            # reg = getself.__class__(reg)  # 2x2?
            wh = argcheck.getvector(wh)

            # xc = reg[0]
            # yc = reg[1]
            # if len(wh) == 1:
            #     w = np.round(wh/2)
            #     h = w
            # else:
            #     w = np.round(wh[0]/2)
            #     h = np.round(wh[1]/2)
            # left = xc - w
            # right = xc + w
            # top = yc - h
            # bot = yc + h

            left, right, top, bottom = reg

        elif reg is not None and wh is None:
            # reg = getself.__class__(reg)
            if len(reg) == 2:
                left = reg[0, 0]
                right = reg[0, 1]
                top = reg[1, 0]
                bot = reg[1, 1]
            elif len(reg) == 4:
                left, right, top, bot = reg

        else:
            raise ValueError(reg, 'reg cannot be None')

        # TODO check row/column ordering, and ndim check
        out = []
        for im in self:
            roi = im.image[top:bot, left:right]

            out.append(roi)

        return self.__class__(out, colororder=self.colororder)
    def samesize(self, im2, bias=0.5):
        """
        Automatic image trimming

        :param im2: image 2
        :type im2: numpy array
        :param bias: bias that controls what part of the image is cropped
        :type bias: float
        :return out: Image with trimmed image
        :rtype out: Image instance

        ``IM.samesize(im2)`` is an image that has the same dimensions as
        ``im2``.  This is achieved by cropping and scaling.

        ``IM.samesize(im2, bias)`` as above but ``bias`` controls which part of
        the image is cropped.  ``bias`` = 0.5 is symmetric cropping, ``bias`` <
        0.5 moves the crop window up or to the left, while ``bias``>0.5 moves
        the crop window down or to the right.

        Example:

        .. runblock:: pycon

        """
        # check inputs
        if bias < 0 or bias > 1:
            raise ValueError(bias, 'bias must be in range [0, 1]')

        im = self.image

        sc = np.r_[im2.shape[:2]] / np.r_[im.shape[:2]]
        o = self.scale(sc.max())

        if o.height > im2.width:  # rows then columns
            # scaled image is too high, so trim rows
            d = o.height - im2.height
            d1 = max(1, int(np.floor(d * bias)))
            d2 = d - d1
            # [1 d d1 d2]
            o = o.image[d1:-d2, :, :]  # TODO check indexing
        if o.width > im2.width:
            # scaled image is too wide, so trim columns
            d = o.width - im2.width
            d1 = max(1, int(np.floor(d * bias)))
            d2 = d - d1
            # [2 d d1 d2]
            out = o.image[:, d1:-d2, :]  # TODO check indexing


        return self.__class__(out, colororder=self.colororder)

    def scale(self, sfactor, outsize=None, sigma=None, interpolation=None):
        """
        Scale an image

        :param sfactor: scale factor
        :type sfactor: scalar
        :param outsize: output image size (w, h)
        :type outsize: 2-element vector, integers
        :param sigma: standard deviation of kernel for image smoothing
        :type sigma: float
        :return out: Image smoothed image
        :rtype out: Image instance

        - ``IM.scale(sfactor)`` is a scaled image in both directions by
          ``sfactor`` which is a real scalar. ``sfactor> 1`` makes the image
          larger, ``sfactor < 1`` makes it smaller.

        - ``IM.scale(sfactor, outsize)`` as above, with the output image size
          specified as (W, H).

        - ``IM.scale(sfactor, sigma)`` as above, with the initial Gaussian
          smoothing specified as ``sigma``.

        Example:

        .. runblock:: pycon

        """
        # check inputs
        if not smb.isscalar(sfactor):
            raise TypeError(sfactor, 'factor is not a scalar')

        if interpolation is None:
            if sfactor > 1:
                interpolation = cv.INTER_CUBIC
            else:
                interpolation = cv.INTER_CUBIC
        elif isinstance(interpolation, str):
            if interpolation == 'cubic':
                interpolation = cv.INTER_CUBIC
            elif interpolation == 'linear':
                interpolation = cv.INTER_LINEAR
            elif interpolation == 'area':
                interpolation = cv.INTER_AREA
            else:
                raise ValueError('bad interpolation string')
        else:
            raise TypeError('bad interpolation value')

        if sfactor < 1 and sigma is not None:
            im = self.smooth(sigma)
        else:
            im = self
        out = cv.resize(im.image, None, fx=sfactor, fy=sfactor, 
            interpolation=interpolation)

        return self.__class__(out, colororder=self.colororder)

    _interp_dict = {

'nearest': cv.INTER_NEAREST, # nearest neighbor interpolation
'linear': cv.INTER_LINEAR, #bilinear interpolation
'cubic': cv.INTER_CUBIC, # bicubic interpolation
'area': cv.INTER_AREA, #esampling using pixel area relation. It may be a preferred method for image decimation, as it gives moire'-free results. But when the image is zoomed, it is similar to the INTER_NEAREST method.
'Lanczos': cv.INTER_LANCZOS4, #Lanczos interpolation over 8x8 neighborhood
'linear exact': cv.INTER_LINEAR_EXACT, # Bit exact bilinear interpolation
    }

    def affine_warp(self, M, inverse=False, size=None, bgcolor=None):
        flags = cv.INTER_CUBIC
        if inverse:
            flags |= cv.WARP_INVERSE_MAP
        
        # TODO interpolation flags
        
        if size is None:
            size = self.shape[:2]

        if bgcolor is not None:
            bordermode = cv.BORDER_CONSTANT
            bordervalue = [bgcolor,] * self.nplanes
        else:
            bordermode = None
            bordervalue = None

        out = cv.warpAffine(src=self.image, M=M, dsize=size, flags=flags, borderMode=bordermode, borderValue=bordervalue)
        return self.__class__(out, colororder=self.colororder)

    def undistort(self, C, dist):
        undistorted = cv.undistort(self.image, C, dist)
        return self.__class__(undistorted, colororder=self.colororder)

    def rotate(self,
               angle,
               crop=False,
               centre=None):
        """
        Rotate an image

        :param angle: rotatation angle [radians]
        :type angle: scalar
        :param crop: output image size (w, h)
        :type crop: 2-element vector, integers
        :param sc: scale factor
        :type sc: float
        :param extrapval: background value of pixels
        :type extrapval: float
        :param sm: smooth (standard deviation of Gaussian kernel, sigma)
        :type sm: float
        :param outsize: output image size (w, h)
        :type outsize: 2-element vector, integers
        :return out: Image with rotated image
        :rtype out: Image instance

        - ``IM.rotate(angle)`` is an image that has been rotated about its
          centre by angle ``angle``.

        - ``IM.rotate(angle, crop)`` as above, but cropped to the same size as
          the original image.

        - ``IM.rotate(angle, scale)`` as above, with scale specified.

        - ``IM.rotate(angle, smooth)`` as above, with initial smoothing
          applied.

        - ``IM.rotate(angle, outsize)`` as above, with size of output image set
          to ``outsize = (H, W)``.

        - ``IM.rotate(angle, extrapval)`` set background pixels to extrapval.
          TODO

        Example:

        .. runblock:: pycon

        .. note::

            - Rotation is defined with respect to a z-axis which is into the
              image.
            - Counter-clockwise is a positive angle.
            - The pixels in the corners of the resulting image will be
              undefined and set to the 'extrapval'.

        """
        # TODO note that there is cv.getRotationMatrix2D and cv.warpAffine
        # https://appdividend.com/2020/09/24/how-to-rotate-an-image-in-python-
        # using-opencv/

        if not smb.isscalar(angle):
            raise ValueError(angle, 'angle is not a valid scalar')

        # TODO check optional inputs


        if centre is None:
            centre = (self.width / 2, self.height / 2)
        elif len(centre) != 2:
            raise ValueError('centre must be length 2')

        shape = (self.width, self.height)

        M = cv.getRotationMatrix2D(centre, np.degrees(angle), 1.0)

        out = cv.warpAffine(self.A, M, shape)
        return self.__class__(out, colororder=self.colororder)

     # ------------------------- operators ------------------------------ #

    def column(self):
        """
        Convert image to a column view

        :return: column view
        :rtype: ndarray(N,) or ndarray(N, np)

        A 2D image is converted to a 1D image in C order, ie. row 0, row 1 etc.
        A 3D image is converted to a 2D image with one row per pixel, and
        each row is the pixel value, the values of its planes.

        .. note:: This creates a view of the original image, so operations on
            the column will affect the original image.
        """
        image = self.image
        if image.ndim == 2:
            return image.reshape((-1,))
        elif image.ndim == 3:
            return image.reshape((-1, self.nplanes))
            
    def col2im(col, im):
        """
        Convert pixel vector to image

        :param col: set of pixel values
        :type col: numpy array, shape (N, P)
        :param im: image
        :type im: numpy array, shape (N, M, P), or a 2-vector (N, M)
        indicating image size
        :return: image of specified shape
        :rtype: numpy array

        - ``col2im(col, imsize)`` is an image (H, W, P) comprising the pixel
            values in col (N,P) with one row per pixel where N=HxW. ``imsize`` is
            a 2-vector (N,M).

        - ``col2im(col, im)`` as above but the dimensions of the return are the
            same as ``im``.

        .. note::

            - The number of rows in ``col`` must match the product of the
                elements of ``imsize``.

        :references:

            - Robotics, Vision & Control, Chapter 10, P. Corke, Springer 2011.
        """

        # col = argcheck.getvector(col)
        col = np.array(col)
        if col.ndim == 1:
            nc = 1
        elif col.ndim == 2:
            nc = col.shape[1]
        else:
            raise ValueError(col, 'col does not have valid shape')

        # second input can be either a 2-tuple/2-array, or a full image
        im = np.array(im)  # ensure we can use ndim and shape
        if im.ndim == 1:
            # input is a tuple/1D array
            sz = im
        elif im.ndim == 2:
            im = Image.getimage(im)
            sz = im.shape
        elif im.ndim == 3:
            im = Image.getimage(im)
            sz = np.array([im.shape[0], im.shape[1]])  # ignore 3rd channel
        else:
            raise ValueError(im, 'im does not have valid shape')

        if nc > 1:
            sz = np.hstack((sz, nc))

        # reshape:
        # TODO need to test this
        return np.reshape(col, sz)

if __name__ == "__main__":

    from machinevisiontoolbox import Image
    from math import pi
    

    img = Image.Read('monalisa.png', reduce=10, grey=False)
    print(img)

    tiles = [img for i in range(19)]
    Image.Tile(tiles).disp(block=True)

    # img.scale(.5).disp()

    # im2 = img.scale(2)
    # im2.disp(block=True)

    # img.rotate(pi / 4, centre=(0,0)).disp()

    # im2 = img.rotate(pi / 4)
    # im2.disp(block=True)
