from typing import Tuple
from lxml import etree

import seaborn as sns

from dlc2labelstudio.dlc_data import is_multianimal


def create_label_config(dlc_config: dict, palette: str='bright') -> str:
    ''' Create a labeling configuration based on DLC configuration

    Parameters:
    dlc_config (dict): DLC project configuration
    palette (str): seaborn color palette to select colors from for keypoint labels

    Returns:
    str - string containing the label studio labeling configuration.
    '''
    root = etree.Element('View', style='display: flex;')
    root.append(create_image_labeling_config())

    labeling_root = etree.SubElement(root, 'View', style='flex: 10%; margin-left: 1em')

    if is_multianimal(dlc_config):
        labeling_root.extend(create_multianimal_bodyparts_labeling_config(dlc_config))

    else:
        labeling_root.append(etree.Element('Header', value="Bodyparts"))
        labeling_root.append(create_bodyparts_labeling_config(dlc_config, palette=palette))


    return etree.tostring(root, pretty_print=True, encoding="unicode")


def create_image_labeling_config(image_name='image', image_value='$image'):
    root = etree.Element('View', style='flex: 90%')
    root.append(etree.Element('Image', name=image_name, value=image_value, width="750px", maxWidth="1000px", zoom="true", zoomControl="true", brightnessControl="true", contrastControl="true"))
    return root


def create_bodyparts_labeling_config(dlc_config: dict, palette: str='bright') -> str:
    kpl = etree.Element('KeyPointLabels', name='keypoint-label', toName='image', strokewidth='2', opacity='1')
    colors = sns.color_palette(palette, len(dlc_config['bodyparts']))
    for bp, color in zip(dlc_config['bodyparts'], colors):
        color = float_rgb_to_int_rgb(color)
        kpl.append(etree.Element('Label', value=bp, background=rgb_to_hex(color)))

    return kpl


def create_multianimal_bodyparts_labeling_config(dlc_config: dict, palette: str='bright') -> str:
    elements = []

    # create labels for individuals, as bounding box annotations
    indv_labels = etree.Element('RectangleLabels', name='individuals', toName='image', maxUsages='1')
    colors = sns.color_palette(palette, len(dlc_config['individuals']))
    for bp, color in zip(dlc_config['individuals'], colors):
        color = float_rgb_to_int_rgb(color)
        indv_labels.append(etree.Element('Label', value=bp, background=rgb_to_hex(color)))
    elements.append(etree.Element('Header', value="Individuals"))
    elements.append(indv_labels)

    mabp_labels = etree.Element('KeyPointLabels', name='mabp', toName="image")
    colors = sns.color_palette(palette, len(dlc_config['multianimalbodyparts']))
    for bp, color in zip(dlc_config['multianimalbodyparts'], colors):
        color = float_rgb_to_int_rgb(color)
        mabp_labels.append(etree.Element('Label', value=bp, background=rgb_to_hex(color)))
    elements.append(etree.Element('Header', value="Multi-Animal Bodyparts"))
    elements.append(mabp_labels)

    uniqbp_labels = etree.Element('KeyPointLabels', name='uniqbp', toName="image", maxUsages='1')
    colors = sns.color_palette(palette, len(dlc_config['uniquebodyparts']))
    for bp, color in zip(dlc_config['uniquebodyparts'], colors):
        color = float_rgb_to_int_rgb(color)
        uniqbp_labels.append(etree.Element('Label', value=bp, background=rgb_to_hex(color)))
    elements.append(etree.Element('Header', value="Unique Bodyparts"))
    elements.append(uniqbp_labels)

    return elements




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
