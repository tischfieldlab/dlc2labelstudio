from typing import Tuple

import seaborn as sns


def create_label_config(dlc_config: dict, palette: str='bright') -> str:
    ''' Create a labeling configuration based on DLC configuration

    Parameters:
    dlc_config (dict): DLC project configuration
    palette (str): seaborn color palette to select colors from for keypoint labels

    Returns:
    str - string containing the label studio labeling configuration.
    '''
    template = '<View style="display: flex;">\n' \
             + '    <View style="flex: 90%">\n' \
             + '        <Image name="image" value="$image" width="750px" maxWidth="1000px" zoom="true" zoomControl="true" brightnessControl="true" contrastControl="true" />\n' \
             + '    </View>\n' \
             + '    <View style="flex: 10%; margin-left: 1em">\n' \
             + '        <Header value="Keypoints" />\n' \
             + '        <KeyPointLabels name="keypoint-label" toName="image" strokewidth="2" opacity="1" >\n'

    colors = sns.color_palette(palette, len(dlc_config['bodyparts']))
    for bp, color in zip(dlc_config['bodyparts'], colors):
        color = float_rgb_to_int_rgb(color)

        template += (' ' * 4 * 3) + f'<Label value="{bp}" background="{rgb_to_hex(color)}"/>'

    template += '        </KeyPointLabels>\n' \
             +  '    </View>\n' \
             +  '</View>\n'

    return template


def float_rgb_to_int_rgb(color: Tuple[float, float, float]) -> Tuple[int, int, int]:
    ''' Convert float format RGB (range 0-1) to int format RGB (range 0-255)

    Parameters:
    color (Tuple[float, float, float]): color with float values in the range 0-1

    Returns:
    Tuple[int, int, int] - the color with all values as ints in the range 0-255
    '''
    return (int(c * 255) for c in color)


def clamp_rgb(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    ''' Ensure all values in color are 0-255

    Parameters:
    color (Tuple[int, int, int]): Tuple of ints

    Returns:
    Tuple[int, int, int] - the color with all values in the range 0-255
    '''
    return (int(max(0, min(c, 255))) for c in color)


def rgb_to_hex(color: Tuple[int, int, int]) -> str:
    ''' Convert a tuple of 8-bit RGB values to HEX notation

    Values are inforced to be between 0 and 255

    Parameters:
    color (Tuple[int, int, int]): Tuple of ints in the range of 0-255

    Returns:
    str - the color in HEX notation
    '''
    r, g, b = clamp_rgb(color)
    return f'#{r:02x}{g:02x}{b:02x}'
