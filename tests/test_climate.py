"""Small numerical checks for the climate-exposure routines."""

from __future__ import annotations

import importlib.util
import io
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exposure = load_module(
    "exposure", ROOT / "climate" / "cyclone" / "02_build_exposure.py"
)
combine = load_module("combine", ROOT / "climate" / "combine_and_validate.py")


class CycloneTests(unittest.TestCase):
    def test_haversine_zero_and_symmetry(self):
        zero = exposure.haversine(22.0, 90.0, 22.0, 90.0)
        forward = exposure.haversine(22.0, 90.0, 23.0, 91.0)
        reverse = exposure.haversine(23.0, 91.0, 22.0, 90.0)
        self.assertAlmostEqual(float(zero), 0.0)
        self.assertAlmostEqual(float(forward), float(reverse))

    def test_storm_wind_at_radius_of_maximum_wind(self):
        storm = pd.DataFrame(
            [{
                "LAT": 20.0,
                "LON": 90.0,
                "rmw_km": 20.0,
                "holland_b": 1.5,
                "bearing_deg": 0.0,
                "vmax_ms_1min": 50.0,
                "forward_ms": 0.0,
            }]
        )
        latitude = np.array([20.0 + np.degrees(20.0 / exposure.EARTH_RADIUS_KM)])
        peak, hours_34, hours_64, cubic = exposure.model_storm(
            storm, latitude, np.array([90.0])
        )
        self.assertAlmostEqual(float(peak[0]), 40.0, places=8)
        self.assertEqual(int(hours_34[0]), 1)
        self.assertEqual(int(hours_64[0]), 1)
        self.assertAlmostEqual(float(cubic[0]), 40.0**3, places=5)

    def test_area_mean_uses_weights(self):
        result = exposure.area_mean(
            np.array([10.0, 20.0, 5.0]),
            np.array([0, 0, 1]),
            np.array([1.0, 3.0, 2.0]),
            np.array([4.0, 2.0]),
        )
        np.testing.assert_allclose(result, [17.5, 5.0])


class PanelTests(unittest.TestCase):
    def test_duplicate_upazila_year_is_rejected(self):
        source = io.StringIO("adm3_pcode,year\nBD01,2020\nBD01,2020\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            combine.read_panel(source, "test")


if __name__ == "__main__":
    unittest.main()

