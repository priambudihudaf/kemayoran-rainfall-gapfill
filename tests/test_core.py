"""Offline checks; no private observations, Google account, or network required."""
import sys
import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from run_analysis import station_data, metrics, choose_mask
from extract_satellite_gee import _chunks, _get_region_to_frame

class FakePointCollection:
    def getRegion(self, *_):
        class R:
            def getInfo(self):
                return [["id","longitude","latitude","time","precipitation"],
                        ["first",106.84,-6.15,1704067200000,2.4],
                        ["second",106.84,-6.15,1704069000000,4.6]]
        return R()

class ResearchCoreTests(unittest.TestCase):
    def test_missing_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.csv"
            pd.DataFrame({"date":["2024-01-01","2024-01-02","2024-01-03"],"gauge_mm":[0,8888,12]}).to_csv(p,index=False)
            result=station_data(p)
            self.assertTrue(pd.isna(result.loc[1,"gauge_mm"]))
            self.assertEqual(result.loc[0,"gauge_mm"],0)
    def test_station_absent(self):
        with self.assertRaises(FileNotFoundError):
            station_data("/nonexistent/fixture.csv")
    def test_extreme_recall(self):
        m=metrics([0,60,80,0],[0,30,100,0],threshold=50)
        self.assertEqual(m["false_negative"],1)
        self.assertAlmostEqual(m["recall"],0.5)
    def test_no_extremes_is_not_zero_recall(self):
        self.assertTrue(np.isnan(metrics([0,1],[0,0],threshold=10)["recall"]))
    def test_chunk_dates(self):
        self.assertEqual(list(_chunks("2020-01-01","2020-08-15",months=3)),
                         [("2020-01-01","2020-04-01"),("2020-04-01","2020-07-01"),("2020-07-01","2020-08-15")])
    def test_point_parser(self):
        result=_get_region_to_frame(FakePointCollection(),object(),11132)
        self.assertEqual(len(result),2)
        self.assertAlmostEqual(result["value"].sum()*0.5,3.5)
    def test_mask_valid_only(self):
        dates=pd.date_range("2024-01-01","2024-12-31")
        rng=np.random.default_rng(44)
        df=pd.DataFrame({"date":dates,"gauge_mm":rng.uniform(0,100,len(dates)),
                         "chirps3_rnl_mm":rng.uniform(0,100,len(dates)),
                         "imerg_v07_mm":rng.uniform(0,100,len(dates))})
        df.loc[:12,"gauge_mm"]=np.nan
        ix=choose_mask(df,"block7",0.10,np.random.default_rng(12))
        self.assertTrue(df.iloc[ix]["gauge_mm"].notna().all())
        self.assertGreater(len(ix),20)

if __name__=="__main__":
    unittest.main()
