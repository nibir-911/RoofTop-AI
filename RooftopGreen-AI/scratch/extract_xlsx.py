import zipfile
import xml.etree.ElementTree as ET
import json
import sys

def parse_xlsx(file_path):
    with zipfile.ZipFile(file_path) as z:
        # 1. Parse shared strings
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                # concatenate all t text inside si
                texts = [t.text for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text]
                shared_strings.append(''.join(texts))

        # 2. Parse sheet1.xml
        sheet_tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        sheet_data = sheet_tree.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData')

        rows = []
        for row in sheet_data.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            row_data = {}
            for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                r_attr = c.attrib.get('r', '') # e.g. A1, B1
                t_attr = c.attrib.get('t', '') # s for shared string
                val_elem = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                if val_elem is not None and val_elem.text is not None:
                    v = val_elem.text
                    if t_attr == 's':
                        val = shared_strings[int(v)]
                    else:
                        val = v
                else:
                    # check if inlineStr
                    is_elem = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
                    if is_elem is not None:
                        val = ''.join([t.text for t in is_elem.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text])
                    else:
                        val = ''
                # extract column letters
                col_letter = ''.join([ch for ch in r_attr if ch.isalpha()])
                row_data[col_letter] = val
            rows.append(row_data)

        if not rows:
            return []

        # Header row
        headers = rows[0]
        result = []
        for r in rows[1:]:
            obj = {}
            for col, header_name in headers.items():
                obj[header_name.strip()] = r.get(col, '')
            result.append(obj)
        return result

if __name__ == '__main__':
    path = sys.argv[1]
    res = parse_xlsx(path)
    print(f"File: {path}")
    print(f"Total rows: {len(res)}")
    if res:
        print("Columns:", list(res[0].keys()))
        print("Sample row 1:", json.dumps(res[0], indent=2))
        print("Sample row 2:", json.dumps(res[1], indent=2))
