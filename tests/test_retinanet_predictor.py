# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import torch
from parameterized import parameterized

from monai.apps.detection.networks.retinanet_predictor import DictPredictor
from monai.inferers import SlidingWindowInferer
from monai.networks import eval_mode, train_mode
from tests.utils import test_script_save

TEST_CASE_1 = [  # 3D, batch 3, 2 input channel
    {
        "pretrained": False,
        "spatial_dims": 3,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": 7,
        "conv1_t_stride": (2, 2, 2),
    },
    (3, 2, 32, 64, 48),
]

TEST_CASE_2 = [  # 2D, batch 2, 1 input channel
    {
        "pretrained": False,
        "spatial_dims": 2,
        "n_input_channels": 1,
        "num_classes": 3,
        "conv1_t_size": [7, 7],
        "conv1_t_stride": [2, 2],
    },
    (2, 1, 32, 64),
]

TEST_CASE_2_A = [  # 2D, batch 2, 1 input channel, shortcut type A
    {
        "pretrained": False,
        "spatial_dims": 2,
        "n_input_channels": 1,
        "num_classes": 3,
        "shortcut_type": "A",
        "conv1_t_size": (7, 7),
        "conv1_t_stride": 2,
    },
    (2, 1, 32, 64),
]

TEST_CASE_3 = [  # 1D, batch 1, 2 input channels
    {
        "pretrained": False,
        "spatial_dims": 1,
        "n_input_channels": 2,
        "num_classes": 3,
        "conv1_t_size": [3],
        "conv1_t_stride": 1,
    },
    (1, 2, 32),
]

TEST_CASE_3_A = [  # 1D, batch 1, 2 input channels
    {"pretrained": False, "spatial_dims": 1, "n_input_channels": 2, "num_classes": 3, "shortcut_type": "A"},
    (1, 2, 32),
]

TEST_CASE_4 = [  # 2D, batch 2, 1 input channel
    {"pretrained": False, "spatial_dims": 2, "n_input_channels": 1, "num_classes": 3, "feed_forward": False},
    (2, 1, 32, 64),
]

TEST_CASES = []
TEST_CASES = [TEST_CASE_1, TEST_CASE_2, TEST_CASE_2_A]

TEST_CASES_TS = [TEST_CASE_1]


class NaiveNetwork(torch.nn.Module):
    def __init__(self, spatial_dims, num_classes, **kwargs):
        super().__init__()
        self.spatial_dims = spatial_dims
        self.num_classes = num_classes
        self.num_anchors = 1
        self.cls_key = "cls"
        self.box_reg_key = "box_reg"
        self.size_divisible = 1

    def forward(self, images):
        out_cls_shape = (images.shape[0], self.num_classes * self.num_anchors) + images.shape[-self.spatial_dims :]
        out_box_reg_shape = (images.shape[0], 2 * self.spatial_dims * self.num_anchors) + images.shape[
            -self.spatial_dims :
        ]
        return {self.cls_key: [torch.randn(out_cls_shape)] * 2, self.box_reg_key: [torch.randn(out_box_reg_shape)] * 2}


class TestPredictor(unittest.TestCase):
    @parameterized.expand(TEST_CASES)
    def test_naive_predictor(self, input_param, input_shape):
        net = NaiveNetwork(**input_param)
        inferer = SlidingWindowInferer(roi_size=128, overlap=0.25, cache_roi_weight_map=True)
        predictor = DictPredictor(net, network_output_keys=["cls", "box_reg"], inferer=inferer)

        with eval_mode(predictor):
            input_data = torch.randn(input_shape)
            result = predictor.inference(input_data, use_inferer=False)
            assert len(result["cls"]) == 2

            result = predictor.inference(input_data, use_inferer=True)
            assert len(result["cls"]) == 2

    @parameterized.expand(TEST_CASES_TS)
    def test_script(self, input_param, input_shape):
        # test whether support torchscript
        net = NaiveNetwork(**input_param)
        inferer = SlidingWindowInferer(roi_size=128, overlap=0.25, cache_roi_weight_map=True)
        predictor = DictPredictor(net, network_output_keys=["cls", "box_reg"], inferer=inferer)

        with train_mode(predictor):
            input_data = torch.randn(input_shape)
            test_script_save(predictor, input_data)


if __name__ == "__main__":
    unittest.main()
