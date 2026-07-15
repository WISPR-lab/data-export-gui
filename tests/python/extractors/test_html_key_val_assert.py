import os
from python_core.extractors.html_key_val import HTMLKeyValParser

def run_test():
    filepath = "/Users/julianonn/uw/takeout-tool/tests/zip_data/google/Devices*.html"
    with open(filepath, "r") as f:
        content = f.read()
    
    parser = HTMLKeyValParser()
    records = parser.extract(content)
    
    assert len(records) == 1, f"Expected 1 record, got {len(records)}"
    record = records[0]
    
    # Assert some key values
    assert record.get("Android ID") == "4504852903928532480", f"Unexpected Android ID: {record.get('Android ID')}"
    assert record.get("IMEI(s)") == "358041083031635", f"Unexpected IMEI: {record.get('IMEI(s)')}"
    assert record.get("Serial Number(s)") == "joan:VS996c4dca425", f"Unexpected Serial: {record.get('Serial Number(s)')}"
    assert record.get("Manufacturer") == "LGE", f"Unexpected Manufacturer: {record.get('Manufacturer')}"
    assert record.get("Model") == "VS996", f"Unexpected Model: {record.get('Model')}"
    assert record.get("IP address from Last Data Connection") == "174.214.12.225", f"Unexpected IP: {record.get('IP address from Last Data Connection')}"
    
    # Check that CSS is not scooped up
    for k in record.keys():
        assert not k.startswith("table"), f"CSS leaked into keys: {k}"
        assert "border-collapse" not in record[k], f"CSS leaked into values: {record[k]}"
        
    print("HTMLKeyValParser self-check passed successfully!")

if __name__ == "__main__":
    run_test()
