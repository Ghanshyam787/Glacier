import os, sys, shutil, subprocess, tempfile, unittest
os.environ["GLACIER_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import devkb, registry
import tools
from tools import dev


class KnowledgeBase(unittest.TestCase):
    def test_counts_and_metadata(self):
        s = devkb.stats()
        self.assertGreaterEqual(s["c"], 10)
        self.assertGreaterEqual(s["cpp"], 10)
        self.assertGreaterEqual(s["html"], 8)
        self.assertGreater(s["ref_sections"], 40)
        for e in devkb.examples():
            self.assertTrue(e["desc"] and e["keywords"], e["file"])

    def test_search(self):
        self.assertIn("undefined reference", devkb.search_ref("undefined reference linker", "c"))
        self.assertIn("unordered_map", devkb.search_ref("unordered_map hash", "cpp"))
        self.assertIn("flex", devkb.search_ref("flexbox center", "html").lower())
        self.assertEqual(devkb.search_ref("", "c"), "")
        names = [e["name"] for e in devkb.find_examples("bank account oop", "cpp")]
        self.assertIn("bank_system", names)

    def test_tools_registered_and_work(self):
        for n in ("dev_reference", "list_examples", "use_example", "lookup_docs"):
            self.assertIn(n, registry.TOOLS)
        self.assertIn("bst", dev.list_examples("c"))
        self.assertIn("segmentation", dev.dev_reference("segmentation fault", "c").lower())

    def test_use_example_copies(self):
        base = os.path.join(os.path.expanduser("~"), "gl_devkb_unit")
        shutil.rmtree(base, ignore_errors=True)
        self.addCleanup(shutil.rmtree, base, True)
        d = os.path.join(base, "proj")
        r = dev.use_example("todo_app", "html", d)
        self.assertIn("copy ho gaya", r)
        self.assertTrue(os.path.exists(os.path.join(d, "index.html")))
        self.assertIn("pehle se bhara", dev.use_example("todo_app", "html", d))
        self.assertIn("nahi mila", dev.use_example("no_such_example", "", os.path.join(d, "x")))

    def test_html_examples_pass_check(self):
        for e in devkb.examples("html"):
            out = dev.check_html(e["path"])
            self.assertNotIn("ERROR", out.upper().replace("0 ERROR", ""), f"{e['file']}: {out[:300]}")

    @unittest.skipUnless(shutil.which("gcc") and shutil.which("g++"), "gcc/g++ nahi mila")
    def test_all_examples_compile_clean(self):
        tmp = tempfile.mkdtemp()
        for e in devkb.examples("c") + devkb.examples("cpp"):
            exe = os.path.join(tmp, e["name"])
            cmd = (["gcc", "-std=c11"] if e["lang"] == "c" else ["g++", "-std=c++17", "-pthread"]) + \
                  ["-Wall", "-Wextra", "-Wpedantic", "-Werror", e["path"], "-o", exe] + (["-lm"] if e["lang"] == "c" else [])
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{e['file']}: {r.stderr[:400]}")


class OfflineDocs(unittest.TestCase):
    def test_index_and_search_fake_archives(self):
        import zipfile, docsync
        d = tempfile.mkdtemp()
        z = os.path.join(d, "html-book.zip")
        page = ("<html><head><title>std::unordered_map::try_emplace - cppreference.com</title></head><body><nav>menu</nav>"
                "<h1>std::unordered_map::try_emplace</h1><p>" + "Inserts a new element if the key does not exist. " * 5 + "</p></body></html>")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("reference/en/cpp/container/unordered_map/try_emplace.html", page)
            f.writestr("reference/en/index.html", "<html></html>")
        self.assertEqual(docsync.index_cppreference_archive(z), 1)
        m = os.path.join(d, "mdn.zip")
        md = '---\ntitle: "flex-wrap"\n---\n\nThe **flex-wrap** CSS property sets whether items wrap. {{CSSXref("flex")}} ' + "more words. " * 10
        with zipfile.ZipFile(m, "w") as f:
            f.writestr("content-main/files/en-us/web/css/flex-wrap/index.md", md)
            f.writestr("content-main/files/en-us/glossary/x/index.md", md)
        self.assertEqual(docsync.index_mdn_archive(m), 1)
        self.assertTrue(docsync.is_installed())
        self.assertEqual(docsync.search("try_emplace", "cpp")[0][1], "cppreference")
        self.assertEqual(docsync.search("flex wrap", "html")[0][1], "mdn")
        self.assertEqual(docsync.search("try_emplace", "c"), [])
        self.assertIn("official", dev.dev_reference("try_emplace", "cpp"))
        self.assertIn("[offline", dev.lookup_docs("flex-wrap", "html"))

    def test_download_host_allowlist(self):
        import docsync
        self.assertFalse(docsync._host_ok("https://evil.com/github.com"))
        self.assertFalse(docsync._host_ok("http://github.com/x"))
        self.assertTrue(docsync._host_ok("https://objects.githubusercontent.com/x"))

    def test_install_needs_confirmation(self):
        self.assertIn("CONFIRMATION_NEEDED", dev.install_offline_docs("all"))


class ModelChoice(unittest.TestCase):
    def test_local_model_recommendation(self):
        self.assertEqual(dev.recommend_local_model(16, 0)[0], "qwen2.5-coder:7b")
        self.assertEqual(dev.recommend_local_model(64, 24)[0], "qwen2.5-coder:32b")
        self.assertEqual(dev.recommend_local_model(4, 0)[0], "qwen2.5-coder:1.5b")
        self.assertIn("ollama pull", dev.local_model_advice())

    def test_prefer_model_for_coding(self):
        import engines
        self.assertEqual(engines.candidate_models(["gemini-x-pro"])[0], "gemini-x-pro")
        self.assertNotIn("gemini-x-pro", engines.candidate_models())


if __name__ == "__main__":
    unittest.main()
