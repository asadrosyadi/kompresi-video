import numpy as np
import pandas as pd
from encoder import serialize
from fractions import Fraction  # python module for handling rational numbers


def lfilter(taps, array, filter_centre):
    """
    Applies a FIR filter with symmetric and periodic padding
    M. Rabbani, R. Joshi described the mentioned padding.
    Args:
        taps (list): taps of the FIR filter
        array (np.ndarray): array to be filtered.
        filter_centre (int):the index of the origin tap
            i.e. the index corresponding to h(0), used for padding
    Returns 
        filtered_arrat (np.ndarray): filtered array.
                                    same length as array.
    """
    arr = array.copy()
    left_pad_len = len(taps) - filter_centre - 1
    right_pad_len = filter_centre
    arr = np.concatenate(
        (array[1:1+left_pad_len][::-1], array,
         array[-right_pad_len-1:-1][::-1]))
    return np.convolve(arr, taps[::-1], 'valid')


def check_image(image, depth):
    """
    Check if the image has valid dimensions and if not would resize the image
    to valid dimensions
    (valid dimensions are the divisble by 8 on rows and columns since the max
     level of decompostion is 3)
    Args:
        image (PIL): image input from the user
    Returns:
        image_array(np.ndarray): image array reshaped to be divisible
                                by 2**depth
        aspect_ratio (fractions.Fraction): rational number storing the aspect
                                           ratio
    """
    cols, rows = image.size
    divisor = 2**depth
    n_rows = round(rows/divisor) * divisor
    n_cols = round(cols/divisor) * divisor
    # d = min(n_rows, n_cols)
    image = image.resize((n_cols, n_rows))
    image_array = np.asarray(image)
    return image_array, Fraction(n_rows, n_cols)


def dwt(image_array, quantization_Array):
    """
    Gets an image of arbitrary size
    and return an array of the same size containing 4 different versions of the
    image by filtering the rows and colums using a low pass or a high pass
    filter with the different combinations and quantized by the quantization
    array
    Args:
        image_array (numpy ndarray): Image input we want to transform.
         Should have shape (length, width)

         quantization_Array (List of ints): An array that contains four values
         for the quantization of each image
        should be 1D and have 4 elements
    Returns:
        filtered_image (numpy ndarray): array of the 4 images [LL,LH,HL,HH]
         - should have a shape of (X, box_size, box_size).

    """
    # Create the high pass and low pass filters
    # both filters are non-causal
    # symmetric
    #     [-2,       -1,    0,    1,      2]
    LPF = [-0.125, 0.25, 0.75, 0.25, -0.125]
    LPF_center = 2

    #     [  -2,-1,    0]
    HPF = [-0.5, 1, -0.5]
    HPF_center = 2

    nrow, ncol = image_array.shape

    # create an array that will contain the 4 different subbands of the image
    LL = np.zeros((nrow, ncol))
    LH = np.zeros((nrow, ncol))
    HL = np.zeros((nrow, ncol))
    HH = np.zeros((nrow, ncol))
    filtered_image = [LL, LH, HL, HH]

    # filtering the rows using a low pass and high pass filters
    LowPass_rows = np.zeros((nrow, ncol))
    HighPass_rows = np.zeros((nrow, ncol))
    for i in range(0, nrow):
        LowPass_rows[i, :] = lfilter(LPF, image_array[i, :], LPF_center)
        HighPass_rows[i, :] = lfilter(HPF, image_array[i, :], HPF_center)

    # down sample rows.
    # which means we will have half the number of columns
    for i in range(0, len(filtered_image)):
        filtered_image[i] = filtered_image[i][:, ::2]

    # apply filters accross columns
    for i in range(0, ncol):
        LL[:, i] = lfilter(LPF, LowPass_rows[:, i], LPF_center)
        LH[:, i] = lfilter(HPF, LowPass_rows[:, i], HPF_center)
        HL[:, i] = lfilter(LPF, HighPass_rows[:, i], LPF_center)
        HH[:, i] = lfilter(HPF, HighPass_rows[:, i], HPF_center)

    # down sample columns and quantize
    for i in range(0, len(filtered_image)):
        filtered_image[i] = filtered_image[i][::2, :]
        filtered_image[i] = np.round(
            filtered_image[i]/quantization_Array[i]).astype(int)

    return filtered_image


def dwt_levels(filtered_image, levels, quantization_Array):
    """
    Gets an array of 4 elements (the output of the dwt function)
    and return an array by replacing the elements of the list that are
    addressed through the levels array by dwt versions of them (replace 1
                                             element with a List of 4 elements)

    Args:
        filtered_image (numpy ndarray): The output of the dwt function that
        would be decomposed further.
         should have 4 elements

        quantization_Array (List): An array that contains four values for the
        quantization of each image
        should have 4 elemets

        levels (a list of lists): The parts of the image that will be
        decomposed further.
        the levels should include a list of decompositions for one or more of
        the 4 subbands
        e.g. if I want to decompose subband 0 (LL)
        I should sent [[0]]
        if both 0 and 1 -> [[0], [1]]
        this can be done in a recursive matter, add a similar list next to the
        subband index
        e.g. to decompose LL twize [[0, [[0]] ]]
        to decompose LL then its LL and LH subbands -> [[0, [[0], [1]] ]]
        it helps to think of it as a tree
        The above list means that the LL image would be decomposed again,
        then the new LL and LH that were created from the LL image would
        be decomposed again,
        LL:0
        LH:1
        HL:2
        HH:3

    """
    assert len(levels) <= 4
    for level in levels:
        filtered_image[level[0]] = dwt(
            filtered_image[level[0]], quantization_Array)
        try:
            # continue recursively
            dwt_levels(filtered_image[level[0]],
                       level[1], quantization_Array)
        except IndexError:
            # happens when level has one element
            # we are done, no recursive lists left
            continue


def dwt_serialize(filtered_image, output, length):
    """
    This function takes the output of the dwt_levels and serializes the list.
    The serialization is done by order of apperance in the filtered_image
    e.g.:[[LL,LH,HL,HH],LH,HL,HH] 
    is serialized by taking the first element , if found to be a list then the
    elements within this list
    would each be serialized and appended to to the output list, if found to be
    a numpy array then it would be serialized without further steps.

    args:
    filtered_image(list): This should be a list that can contain either numpy
                            arrays or a list of numpy arrays
    output(list): should be passed as an empty list that will contain the final
                  serialized data of the image
    length(list):should be passed as an empty list that will contain the
             serialized length of each numpy array within the filtered_image


    """
    for i in filtered_image:
        if isinstance(i, list):
            # append the output of the recursion to the main arguments (output,
            # length)
            output_temp, length_temp = dwt_serialize(i, [], [])
            output = output + output_temp
            length.append(length_temp)
        else:
            # append the data of the serialized elements to the main arguments
            # (output,length)
            new_output = (serialize(i, True).tolist())
            output = output+new_output
            length = length+[len(new_output)]
    return output, length
