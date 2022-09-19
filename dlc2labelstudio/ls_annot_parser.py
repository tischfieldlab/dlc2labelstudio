from typing import Dict, Iterable, List


def read_annotations(annotations: List[dict]) -> List[dict]:
    ''' Read annotations from json file output by labelstudio (coco-ish) format

    Parameters:
    annotations (List[dict]): List of label studio task dicts
    keypoint_names (List[str]): list of the keypoint names, in the order desired. If None, ignore keypoints
    mask_format (MaskFormat): 'polygon'|'bitmask', format of the masks to output
    rescale (float): instensity rescaling to apply (by dataset mapper) to image when loading

    Returns:
    List[DataItem] annotations
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

        entry_data = get_annotation_from_entry(entry, key=key)
        completions.extend(entry_data)

    return completions


def get_annotation_from_entry(entry: dict, key: str='annotations') -> List[dict]:
    ''' Parse annotations from an entry
    '''

    if len(entry[key]) > 1:
        print('WARNING: Task {}: Multiple annotations found, only taking the first'.format(entry['id']))

    try:
        # only parse the first entry result
        to_parse = entry[key][0]['result']

        individuals = filter_and_index(to_parse, 'rectanglelabels')
        keypoints = filter_and_index(to_parse, 'keypointlabels')
        relations = build_relation_map(to_parse)
        out = []

        if len(individuals) > 0:
            # multi animal case:
            for indv_id, indv in individuals.items():
                for rel in relations[indv_id]:
                    kpt = keypoints.pop(rel)
                    out.append({
                        'task_id': entry['id'],
                        'file_name': get_image_path(entry),
                        'individual': indv['value']['rectanglelabels'][0],
                        'bodypart': kpt['value']['keypointlabels'][0],
                        'x': (kpt['value']['x'] * kpt['original_width']) / 100,
                        'y': (kpt['value']['y'] * kpt['original_height']) / 100,
                    })

        # If this is multi-animal, any leftover keypoints should be unique bodyparts, and will be collected here
        # if single-animal, we only have 'unique bodyparts' [in a way] and the process is identical
        for _, kpt in keypoints.items():
            out.append({
                'task_id': entry['id'],
                'file_name': get_image_path(entry),
                'individual': None, # None indicates a unique bodypart
                'bodypart': kpt['value']['keypointlabels'][0],
                'x': (kpt['value']['x'] * kpt['original_width']) / 100,
                'y': (kpt['value']['y'] * kpt['original_height']) / 100,
            })

        return out
    except Exception as excpt:
        raise RuntimeError('While working on Task #{}, encountered the following error:'.format(entry['id'])) from excpt


def filter_and_index(annotations: Iterable[dict], annot_type: str) -> Dict[str, dict]:
    ''' Filter annotations based on the type field and index them by ID

    Parameters:
    annotation (Iterable[dict]): annotations to filter and index
    annot_type (str): annotation type to filter e.x. 'keypointlabels' or 'rectanglelabels'

    Returns:
    Dict[str, dict] - indexed and filtered annotations. Only annotations of type `annot_type`
    will survive, and annotations are indexed by ID
    '''
    filtered = list(filter(lambda d: d['type'] == annot_type, annotations))
    indexed = {item['id']: item for item in filtered}
    return indexed


def build_relation_map(annotations: Iterable[dict]) -> Dict[str, List[dict]]:
    ''' Build a two-way relationship map between annotations

    Parameters:
    annotations (Iterable[dict]): annotations, presumably, containing relation types

    Returns:
    Dict[str, List[Dict]]: a two way map of relations indexed by `from_id` and `to_id` fields
    '''
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


def pick_filenames_from_tasks(tasks: List[dict]) -> List[str]:
    ''' Given Label Studio task list, pick and return a list of filenames

    Parameters:
    tasks (List[dict]): List of label studio task dicts

    Returns:
    List[str] - List of filenames from tasks
    '''
    annot = read_annotations(tasks)
    return [a['file_name'] for a in annot]
