# -*- coding: utf-8 -*-
from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _load_pos_data(self, data):
        # Use sudo() to ensure cashiers can always load their shop configuration
        # without being blocked by multi-company mismatches or administrative field restrictions
        return super(PosConfig, self.sudo())._load_pos_data(data)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load, only_data=False):
        # Ensure POS startup data loading is executed with sudo() so that
        # cashiers with restricted backend permissions can load the POS UI without crashing
        return super(PosSession, self.sudo()).load_data(models_to_load, only_data=only_data)
