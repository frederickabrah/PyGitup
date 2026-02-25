import unittest
import os
import shutil
import tempfile
from pygitup.utils.agent_tools import read_file_tool, write_file_tool, patch_file_tool, list_files_tool

class TestAgentTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_write_and_read_file_tool(self):
        path = "test.txt"
        content = "Hello, Agent!"
        
        # Test writing
        res = write_file_tool(path, content)
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(path))
        
        # Test reading
        res = read_file_tool(path)
        self.assertEqual(res["content"], content)

    def test_path_safety_violation(self):
        # Path outside workspace
        path = "/etc/passwd" 
        res = read_file_tool(path)
        self.assertIn("error", res)
        self.assertIn("Security Violation", res["error"])

        res = write_file_tool(path, "malicious")
        self.assertIn("error", res)
        self.assertIn("Security Violation", res["error"])

    def test_patch_file_tool(self):
        path = "patch_test.txt"
        content = "Line 1\nLine 2\nLine 3"
        write_file_tool(path, content)
        
        res = patch_file_tool(path, "Line 2", "Line Two Updated")
        self.assertEqual(res["status"], "success")
        
        res = read_file_tool(path)
        self.assertEqual(res["content"], "Line 1\nLine Two Updated\nLine 3")

        def test_list_files_tool(self):

            write_file_tool("file1.py", "print(1)")

            os.makedirs("subdir", exist_ok=True)

            write_file_tool("subdir/file2.txt", "content")

        

            res = list_files_tool(".")

            files = res["files"]

            # res["files"] is now a list of dicts: {"path": "...", "size_bytes": ..., ...}

            rel_files = [f["path"] for f in files]

            

            self.assertIn("file1.py", rel_files)

            self.assertIn("subdir/file2.txt", rel_files)

    

if __name__ == '__main__':
    unittest.main()
