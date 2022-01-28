import csv
import os
from dataclasses import fields, astuple

from src.files import File


def write_to_csv(data_list: list, outfile: File):
    """Writes `data_list` to `filename` as csv"""
    if len(data_list) == 0:
        print("No data in list, skipping write")
        return
    print(f"dumping {len(data_list)} results to {outfile.name}")
    headers = [f.name for f in fields(data_list[0])]
    data_tuple = [astuple(x) for x in data_list]

    if not os.path.exists(outfile.path):
        os.makedirs(outfile.path)
    with open(outfile.filename(), 'w', encoding='utf-8') as out_file:
        dict_writer = csv.DictWriter(out_file, headers, lineterminator='\n')
        dict_writer.writeheader()
        writer = csv.writer(out_file, lineterminator='\n')
        writer.writerows(data_tuple)


def open_query(filename: str) -> str:
    """Opens `filename` and returns entire file parsed as string"""
    with open(filename, 'r', encoding='utf-8') as query_file:
        return query_file.read()
