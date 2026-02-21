import os
import hashlib

def exists(path):
    # checks if a path (file OR directory) exists without triggering os.stat().
    if not path or path == '/':
        return True
        
    parent = os.path.dirname(path) or '.'
    filename = os.path.basename(path)
    
    # If path is something like "/mnt/data/", basename is empty.
    # We handle that by checking the parent's parent.
    if not filename: 
        return exists(parent)

    try:
        # listdir only returns strings, avoiding the BigInt/NaN metadata crash
        return filename in os.listdir(parent)
    except (FileNotFoundError, OSError):
        return False

def isfile(path):
    # Checks if path is a file. In your flattened OPFS temp store,  if it's in the list, it's a file.
    return exists(path)


def getsize(path):
    try:
        fd = os.open(path, os.O_RDONLY)
        size = os.lseek(fd, 0, os.SEEK_END)
        os.close(fd)
        return size
    except OSError:
        return 0

def read_bytes(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        size = os.lseek(fd, 0, os.SEEK_END)
        os.lseek(fd, 0, os.SEEK_SET)
        
        chunks = []
        bytes_read = 0
        while bytes_read < size:
            chunk = os.read(fd, min(65536, size - bytes_read))
            if not chunk:
                break
            chunks.append(chunk)
            bytes_read += len(chunk)
            
        return b"".join(chunks)
    finally:
        os.close(fd)

def read_text(path, encoding='utf-8', errors='replace'):
    raw_bytes = read_bytes(path)
    return raw_bytes.decode(encoding, errors=errors)


def file_hash(filepath, alg="sha256"):
    hash_object = hashlib.new(alg)
    fd = os.open(filepath, os.O_RDONLY)
    size = os.lseek(fd, 0, os.SEEK_END)
    os.lseek(fd, 0, os.SEEK_SET)
    
    bytes_read = 0
    while bytes_read < size:
        chunk = os.read(fd, min(65536, size - bytes_read))
        if not chunk:
            break
        hash_object.update(chunk)
        bytes_read += len(chunk)
        
    os.close(fd)
    return hash_object.hexdigest()