from data_manager import upload_to_ipfs, download_from_ipfs, publish_to_streamr, subscribe_to_streamr
import os

def test_ipfs():
    # Upload a test file to IPFS
    file_path = 'test.txt'
    with open(file_path, 'w') as f:
        f.write('This is a test file for IPFS.')

    ipfs_hash = upload_to_ipfs(file_path)
    assert ipfs_hash is not None

    # Download the file from IPFS
    download_from_ipfs(ipfs_hash, 'downloaded_test.txt')
    assert os.path.exists('downloaded_test.txt')

    with open('downloaded_test.txt', 'r') as f:
        content = f.read()
    assert content == 'This is a test file for IPFS.'

    os.remove(file_path)
    os.remove('downloaded_test.txt')

def test_streamr():
    stream_id = 'YOUR_STREAM_ID'

    def callback(data):
        print('Received data:', data)

    subscribe_to_streamr(stream_id, callback)

    publish_to_streamr(stream_id, {'message': 'Hello, Streamr!'})

if __name__ == "__main__":
    test_ipfs()
    test_streamr()
    print("All tests passed.")
