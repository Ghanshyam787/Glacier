import os, sys, tempfile, time, unittest
os.environ["GLACIER_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db, notify, scheduler
from tools import reminders as R


def add(text, fire_at, recur="", fired=0, status=""):
    return db.execute("INSERT INTO reminders(text,fire_at,recur,fired,created,status) VALUES(?,?,?,?,?,?)",
                      (text, fire_at, recur, fired, fire_at - 1000, status)).lastrowid


class CatchUp(unittest.TestCase):
    def setUp(self):
        db.execute("DELETE FROM reminders"); db.execute("DELETE FROM tasks")
        self.sent = []
        self._orig = notify.notify
        notify.notify = lambda text, title=None, **k: self.sent.append((title, text))

    def tearDown(self):
        notify.notify = self._orig

    def test_two_days_off_silent_by_default(self):
        now = time.time()
        db.kv_set("last_alive", str(now - 2 * 86400))
        a = add("Mummy ko call", now - 86400)
        b = add("Medicine", now - 1.5 * 86400, "daily")
        c = add("Abhi ka", now - 200)
        d = add("Kal ka", now + 3600)
        scheduler._tick()
        spoken = " ".join(x for _t, x in self.sent)
        self.assertNotIn("Mummy ko call", spoken); self.assertNotIn("Medicine", spoken); self.assertNotIn("Welcome back", spoken)
        self.assertIn("Abhi ka", spoken)                                     # sirf abhi ka (grace ke andar) bola
        row = lambda i: db.query_one("SELECT * FROM reminders WHERE id=?", (i,))
        self.assertEqual((row(a)["fired"], row(a)["status"]), (1, "missed"))  # panel mein 'Chhoote' dikhega
        self.assertGreater(row(b)["fire_at"], now)                             # repeat aage badha, purane time se nahi

    def test_two_days_off(self):
        import config
        config.ANNOUNCE_MISSED = True
        self.addCleanup(setattr, config, "ANNOUNCE_MISSED", False)
        now = time.time()
        db.kv_set("last_alive", str(now - 2 * 86400))
        a = add("Mummy ko call", now - 86400)
        b = add("Medicine", now - 1.5 * 86400, "daily")
        c = add("Abhi ka", now - 200)
        d = add("Kal ka", now + 3600)
        scheduler._tick()
        titles = [t for t, _ in self.sent]
        self.assertEqual(titles.count("Welcome back"), 1)                 # ek hi summary
        summary = [x for t, x in self.sent if t == "Welcome back"][0]
        self.assertIn("Mummy ko call", summary); self.assertIn("Medicine", summary)
        self.assertNotIn("Kal ka", summary)
        row = lambda i: db.query_one("SELECT * FROM reminders WHERE id=?", (i,))
        self.assertEqual((row(a)["fired"], row(a)["status"]), (1, "missed"))
        self.assertEqual(row(b)["fired"], 0); self.assertGreater(row(b)["fire_at"], now)   # repeat aage badha
        self.assertEqual(row(c)["status"], "fired")                          # grace ke andar normal fire
        self.assertEqual(row(d)["fired"], 0)
        self.sent.clear(); scheduler._tick()
        self.assertEqual(self.sent, [])                                       # dobara nahi bolta

    def test_short_gap_no_summary(self):
        db.kv_set("last_alive", str(time.time() - 20))
        scheduler._tick()
        self.assertNotIn("Welcome back", [t for t, _ in self.sent])

    def test_history_not_deleted(self):
        old = add("Bahut purana", time.time() - 90 * 86400, fired=1, status="fired")
        scheduler._tick()
        self.assertIsNotNone(db.query_one("SELECT 1 FROM reminders WHERE id=?", (old,)))

    def test_advance_every_minutes(self):
        nxt, missed = scheduler._advance("every:30", 1000.0, 1000.0 + 3 * 3600 + 10)
        self.assertEqual(missed, 7); self.assertGreater(nxt, 1000.0 + 3 * 3600 + 10)


class Manager(unittest.TestCase):
    def setUp(self):
        db.execute("DELETE FROM reminders")

    def test_add_list_edit_delete(self):
        r = R.reminder_add("Doodh", "in 2 hours")
        self.assertTrue(r["ok"])
        self.assertFalse(R.reminder_add("", "7pm")["ok"])
        self.assertFalse(R.reminder_add("x", "blah blah")["ok"])
        self.assertFalse(R.reminder_add("x", "7pm", "kabhi kabhi")["ok"])
        self.assertEqual(len(R.reminders_all("upcoming")), 1)
        self.assertTrue(R.reminder_update(r["id"], "Doodh aur dahi", "", "daily")["ok"])
        item = R.reminders_all("repeat")[0]
        self.assertEqual((item["text"], item["repeat"]), ("Doodh aur dahi", "daily"))
        self.assertTrue(R.reminder_delete(r["id"])["ok"])
        self.assertFalse(R.reminder_delete(r["id"])["ok"])

    def test_missed_rearm_by_edit(self):
        rid = add("Chhoota", time.time() - 86400, fired=1, status="missed")
        self.assertEqual(len(R.reminders_all("missed")), 1)
        self.assertTrue(R.reminder_update(rid, "Chhoota", "kal 9 baje", "")["ok"])
        self.assertEqual(R.reminders_all("missed"), [])
        self.assertEqual(R.reminders_all("upcoming")[0]["id"], rid)

    def test_filters_and_order(self):
        add("up", time.time() + 100); add("done", time.time() - 500, fired=1, status="fired"); add("miss", time.time() - 900, fired=1, status="missed")
        self.assertEqual([x["status"] for x in R.reminders_all("all")], ["upcoming", "done", "missed"])
        self.assertEqual(len(R.reminders_all("done")), 1)

    def test_tools(self):
        self.assertIn("Abhi tak", R.list_reminders(include_history=True))
        add("Purana", time.time() - 500, fired=1, status="fired")
        self.assertIn("ho chuka", R.list_reminders(include_history=True))
        rid = add("Edit me", time.time() + 5000)
        self.assertIn("Badal", R.edit_reminder(str(rid), text="Edited"))


if __name__ == "__main__":
    unittest.main()
