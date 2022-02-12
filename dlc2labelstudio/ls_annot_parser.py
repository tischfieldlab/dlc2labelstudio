import math
from typing import Dict, Iterable, List, Optional


def read_annotations(annotations: List[dict], keypoint_names: List[str]=None):
    ''' Read annotations from json file output by labelstudio (coco-ish) format

    Parameters:
    annotations (List[dict]): List of label studio task dicts
    keypoint_names (List[str]): list of the keypoint names, in the order desired. If None, ignore keypoints
    mask_format (MaskFormat): 'polygon'|'bitmask', format of the masks to output
    rescale (float): instensity rescaling to apply (by dataset mapper) to image when loading

    Returns:
    Sequence[DataItem] annotations
    '''
    #if keypoint_names is None:
    #    print("WARNING: Ignoring any keypoint information because `keypoint_names` is None.")


    completions = []
    for entry in annotations:
        # depending version, we have seen keys `annotations` and `completions`
        if 'annotations' in entry:
            key = 'annotations'
        elif 'completions' in entry:
            key = 'completions'
        else:
            raise ValueError('Cannot find annotation data for entry!')

        entry_data = get_annotation_from_entry(entry, key=key, keypoint_names=keypoint_names)
        completions.append(entry_data)

    return completions


def get_annotation_from_entry(entry: dict, key: str='annotations', keypoint_names: Optional[List[str]]=None) -> List[dict]:
    ''' Parse annotations from an entry
    '''

    if len(entry[key]) > 1:
        print('WARNING: Task {}: Multiple annotations found, only taking the first'.format(entry['id']))

    # only parse the first entry result
    to_parse = entry[key][0]['result']

    individuals = filter_and_index(to_parse, 'rectanglelabels')
    keypoints = filter_and_index(to_parse, 'keypointlabels')
    relations = build_relation_map(to_parse)
    out = []

    if len(individuals) > 1:
        # multi animal case:
        for indv_id, indv in individuals.items():
            for rel in relations[indv_id]:
                kpt = keypoints[rel]
                out.append({
                    'task_id': entry['id'],
                    'file_name': get_image_path(entry),
                    'individual': indv['value']['rectanglelabels'][0],
                    'bodypart': kpt['value']['keypointlabels'][0],
                    'x': (kpt['value']['x'] * kpt['original_width']) / 100,
                    'y': (kpt['value']['y'] * kpt['original_height']) / 100,
                })

    else:
        # single animal case
        for _, kpt in keypoints.items():
            out.append({
                'task_id': entry['id'],
                'file_name': get_image_path(entry),
                'individual': None,
                'bodypart': kpt['value']['keypointlabels'][0],
                'x': (kpt['value']['x'] * kpt['original_width']) / 100,
                'y': (kpt['value']['y'] * kpt['original_height']) / 100,
            })

    return out

    # for rslt in to_parse:

    #     if rslt['type'] == 'keypointlabels':
    #         if 'points' in rslt['value']:
    #             #print('Skipping unexpected points in keypoint', rslt)
    #             continue
    #         try:
    #             kdata = get_keypoint_data(rslt)
    #             kname = list(kdata.keys())[0]
    #             if kname in kpts:
    #                 print('WARNING: Task {}: Keypoint "{}" has already been parsed, replacing value'.format(entry['id'], kname))
    #             kpts.update(kdata)
    #         except:
    #             print(rslt['value'])
    #             raise
    #     elif rslt['type'] == 'rectanglelabels':
    #         # parse rectangle labels
    #         pass

    #     elif rslt['type'] == 'relation':
    #         # parse relations
    #         pass

    #     #elif rslt['type'] == 'polygonlabels':
    #     #    annot.update(get_polygon_data(rslt, mask_format=mask_format))


    # if keypoint_names is not None:
    #     annot['keypoints'] = sort_keypoints(keypoint_names, kpts)
    # else:
    #     annot['keypoints'] = kpts

    # return {
    #     'file_name': get_image_path(entry),
    #     # ignore these here.
    #     # they can break if we do not have results,
    #     # and we do not need them since we are not strict COCO format
    #     #'width': rslt['original_width'],
    #     #'height': rslt['original_height'],
    #     'image_id': entry['id'],
    #     'annotations': [annot],
    # }


def filter_and_index(annotations: Iterable[dict], type: str) -> Dict[str, dict]:
    filtered = list(filter(lambda d: d['type'] == type, annotations))
    indexed = { item['id']: item for item in filtered }
    return indexed


def build_relation_map(annotations: Iterable[dict]) -> Dict[str, List[dict]]:
    relations = list(filter(lambda d: d['type'] == 'relation', annotations))
    relmap = {}
    for rel in relations:
        if rel['from_id'] not in relmap:
            relmap[rel['from_id']] = []
        relmap[rel['from_id']].append(rel['to_id'])

        if rel['to_id'] not in relmap:
            relmap[rel['to_id']] = []
        relmap[rel['to_id']].append(rel['from_id'])
    return relmap


def get_keypoint_data(entry: dict) -> dict:
    ''' Extract keypoint data from an annotation entry
    '''
    return {
        entry['value']['keypointlabels'][0]: {
            'x': (entry['value']['x'] * entry['original_width']) / 100,
            'y': (entry['value']['y'] * entry['original_height']) / 100,
            'v': 2
        }
    }


def get_image_path(entry: dict) -> str:
    ''' Extract image file path from an annotation entry
    '''
    if 'meta' in entry and 'original_file' in entry['meta']:
        return entry['meta']['original_file']
    elif 'task_path' in entry:
        return entry['task_path']
    elif 'data' in entry and 'image' in entry['data']:
        return entry['data']['image']
    elif 'data' in entry and 'depth_image' in entry['data']:
        return entry['data']['depth_image']


def sort_keypoints(keypoint_order: List[str], keypoints: dict):
    ''' Sort `keypoints` to the order specified by `keypoint_order`
    '''
    annot_keypoints = []
    for kp in keypoint_order:
        if kp in keypoints:
            k = keypoints[kp]
            annot_keypoints.extend([k['x'], k['y'], k['v']])
        else:
            #print('missing keypoint {} in {}'.format(kp, entry['id']))
            annot_keypoints.extend([math.nan, math.nan, math.nan])
    return annot_keypoints


def pick_filenames_from_tasks(tasks: List[dict]) -> List[str]:
    ''' Given Label Studio task list, pick and return a list of filenames

    Parameters:
    tasks (List[dict]): List of label studio task dicts

    Returns:
    List[str] - List of filenames from tasks
    '''
    annot = read_annotations(tasks)
    return [a['file_name'] for a in annot]
