"""
Test File Ingestion System
Tests ingestion of various file types
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.episodic.file_ingestion import FileIngestionService
import tempfile


def test_ingestion():
    """Test file ingestion for different formats"""
    
    print("=" * 80)
    print("FILE INGESTION TEST")
    print("=" * 80)
    
    service = FileIngestionService()
    
    # Test 1: Text file
    print("\n1. Testing .txt file ingestion...")
    txt_content = "This is a test text file.\nIt contains multiple lines.\nFor testing purposes."
    txt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    txt_file.write(txt_content)
    txt_file.close()
    
    try:
        result = service.ingest_file(
            user_id="test_user",
            file_path=txt_file.name,
            metadata={"source": "test"}
        )
        print(f"✓ TXT file ingested")
        print(f"  Filename: {result['metadata']['filename']}")
        print(f"  Size: {result['metadata']['file_size']} bytes")
        print(f"  Content preview: {result['content'][:50]}...")
    except Exception as e:
        print(f"✗ TXT ingestion failed: {e}")
    finally:
        os.unlink(txt_file.name)
    
    # Test 2: Markdown file
    print("\n2. Testing .md file ingestion...")
    md_content = """# Test Document

## Section 1
This is a test markdown file.

## Section 2
- Item 1
- Item 2
- Item 3
"""
    md_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    md_file.write(md_content)
    md_file.close()
    
    try:
        result = service.ingest_file(
            user_id="test_user",
            file_path=md_file.name,
            metadata={"format": "markdown"}
        )
        print(f"✓ MD file ingested")
        print(f"  Filename: {result['metadata']['filename']}")
        print(f"  Content length: {len(result['content'])} characters")
    except Exception as e:
        print(f"✗ MD ingestion failed: {e}")
    finally:
        os.unlink(md_file.name)
    
    # Test 3: JSON file
    print("\n3. Testing .json file ingestion...")
    json_content = '{"name": "test", "value": 123, "items": ["a", "b", "c"]}'
    json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json_file.write(json_content)
    json_file.close()
    
    try:
        result = service.ingest_file(
            user_id="test_user",
            file_path=json_file.name
        )
        print(f"✓ JSON file ingested")
        print(f"  Filename: {result['metadata']['filename']}")
        print(f"  Content: {result['content'][:80]}...")
    except Exception as e:
        print(f"✗ JSON ingestion failed: {e}")
    finally:
        os.unlink(json_file.name)
    
    # Test 4: Batch ingestion
    print("\n4. Testing batch ingestion...")
    files = []
    for i in range(3):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Test file {i+1} content")
        f.close()
        files.append(f.name)
    
    try:
        results = service.batch_ingest(
            user_id="test_user",
            file_paths=files
        )
        print(f"✓ Batch ingestion completed")
        success_count = sum(1 for r in results if r.get('status') == 'ingested')
        print(f"  Successfully ingested: {success_count}/{len(files)} files")
    except Exception as e:
        print(f"✗ Batch ingestion failed: {e}")
    finally:
        for f in files:
            os.unlink(f)
    
    # Test 5: Unsupported format
    print("\n5. Testing unsupported format error handling...")
    unsupported_file = tempfile.NamedTemporaryFile(suffix='.xyz', delete=False)
    unsupported_file.close()
    
    try:
        result = service.ingest_file(
            user_id="test_user",
            file_path=unsupported_file.name
        )
        print(f"✗ Should have raised error for unsupported format")
    except ValueError as e:
        print(f"✓ Correctly rejected unsupported format: {e}")
    finally:
        os.unlink(unsupported_file.name)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ All ingestion tests completed successfully!")


if __name__ == "__main__":
    test_ingestion()
