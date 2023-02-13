from encoder import generate_indicies_zigzag, __basis_generator
import numpy as np
from huffman import decode as h_decode


def huffman_decode(huffcoded, code_dict):
    """
    Decodes a string of a List of 0 and 1
     (same choice for decoder and encoder)
    Args:
        huffcoded : List or String of 0s and 1s code to be sent or stored
        code_dict (dict): dict of symbol : code in binary
    Returns:
        rlcoded (numpy ndarray): 1d array
    """
    return h_decode(huffcoded, code_dict)


def run_length_decode(rlcoded):
    """
    Returns 1D array of serialized dct values from an encoded 1D array.
    Args:
        rlcoded  (numpy ndarray): 1d array
          Encoded in decimal not binary [Kasem]
    Returns:
        serialized (numpy ndarray): 1d array
          has shape (X*box_size*box_size*n_channels,)
    """
    # Local Variables
    serialized = []
    i = 0
    while i < len(rlcoded):
        if rlcoded[i] == 0:
            # found some zeros
            # add n number of zeros to result
            # where n is the subsequent number
            serialized.extend([0]*(rlcoded[i+1]+1))
            # take two steps
            i += 2
        else:
            # non-zero number, add it and take one step
            serialized.append(rlcoded[i])
            i += 1
    return np.asarray(serialized)


def deserialize(serialized, n_blocks, n_rows=8, n_cols=8):
    """
    Removes serialization from quantized DCT values.
    Args:
        serialized (numpy ndarray): 1d array
          has shape (X*box_size*box_size*n_channels,)
        n_blocks (int)
            number of blocks
        n_rows (int)
            number of rows used in serialize function
        n_cols (int)
            number of columns used in serialize function
            n_rows = n_cols for DCT but not necessarily in DWT
    Returns:
        quantized (numpy ndarray): array of quantized DCT values.
          - should have a shape of (X, n_rows, n_cols, n_channels)
           with dtype Int
    """
    output = np.zeros((n_blocks, n_rows, n_cols), dtype=np.int16)
    step = 0
    for matrix in output:
        for i, j in generate_indicies_zigzag(n_rows, n_cols):
            matrix[i, j] = serialized[step]
            step += 1

    return output


def dequantize(quantized, quantization_table):
    """
    Divides quantization table on DCT output
    Args:
        quantized (numpy ndarray): array of quantized DCT values
        - should have a shape of (X, box_size, box_size, n_channels)
         with dct applied to all of them
        quantization_table (numpy ndarray): quantization table (matrix)
        - should have a shape of (box_size, box_size)
    Returns:
        dct_values (numpy ndarray): array of DCT values.
          same shape as dct_values but element type ints
    """
    # element by element multiplication. Equivelant to np.multiply()
    return np.array([block * quantization_table for block in quantized])


def idct(dct_values, basis):
    """
    Applies Inverse Discrete Cosine Transform on DCT values:
    Args:
        dct_values (numpy ndarray): should have a shape of (box_size,box_size)
    Returns:
        sub_image (numpy ndarray): image in pixels
         with same size as input
    """
    b = dct_values.shape[0]  # block size

    outblock = np.zeros((b, b))

    for x in range(b):
        for y in range(b):
            outblock = outblock + dct_values[x,y] * basis(x,y) 
            
    return outblock


def apply_idct_to_all(subdivded_dct_values):
    """
    Maps idct to all dct values (transformed images).
    Args:
        subdivided_dct_values (numpy ndarray): array of dct values.
        - should have a shape of (X, box_size, box_size, n_channels).
    Returns:
        divided_image (numpy ndarray): array of divided images
        - should have a shape of (X, box_size, box_size, n_channels)
         with dct applied to all of them
    """
    basis = __basis_generator(subdivded_dct_values.shape[1])
    divided_image = np.array([idct(sub_image, basis) for
                              sub_image in subdivded_dct_values])
    # values can be slightly less than 0.0 e.g -0.5
    # or more than 255 like 255.5
    # that is why we clip.
    # next we round that cast to an 8bit unsigned integer
    return divided_image.clip(min=0, max=255).round().astype(np.uint8)


def get_reconstructed_image(divided_image, n_rows, n_cols, box_size=8):
    """
    Gets an array of (box_size,box_size) pixels
    and returns the reconstructed image
    Args:
        divided_image (numpy ndarray, dtype = "uint8"): array of divided images
        n_rows: number of rows or blocks
        n_cols: number of columns in image
            the number of blocks is n_rows*n_cols
        box_size (int): Size of the box sub images
    Returns:
        reconstructed_image (numpy ndarray): Image reconstructed from the array
        of divided images.

    """
    image_reconstructed = np.zeros((n_rows*box_size, n_cols*box_size), dtype=np.uint8)
    c = 0
    # break down the image into blocks
    for i in range(n_rows):
        for j in range(n_cols):
            image_reconstructed[i*box_size: i*box_size+box_size, 
                                j*box_size:j*box_size+box_size] = divided_image[c]
            c += 1
            
    # If you want to reconvert the output of this function into images,
    #  use the following line:
    # block_image = Image.fromarray(output[idx])

    return image_reconstructed
