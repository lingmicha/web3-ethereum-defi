"""
 Venus Rates Calculation: Refer README.md
"""


from decimal import Decimal
from typing import NamedTuple


class VenusInterestModelParameters(NamedTuple):
    reserve_factor: Decimal
    kink: Decimal
    base_rate_per_block: Decimal
    multiplier_per_block: Decimal
    jump_multiplier_per_block: Decimal

    def __eq__(self, other):
        return abs(self.reserve_factor - other.reserve_factor) < Decimal(10**-6) and \
               abs(self.kink - other.kink) < Decimal(10**-6) and \
               abs(self.base_rate_per_block - other.base_rate_per_block) < Decimal(10**-6) and \
                abs(self.multiplier_per_block - other.multiplier_per_block) < Decimal(10**-6) and \
                abs(self.jump_multiplier_per_block - other.jump_multiplier_per_block) < Decimal(10**-6)


class VenusInterestModel:
    def __init__(self, params:VenusInterestModelParameters):
        self.params = params

    @staticmethod
    def utilization_rate(cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:

        if borrows == Decimal(0):
            return Decimal(0)
        return borrows / (borrows + cash - reserves)

    def borrow_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:
        pass

    def supply_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:
        utilization_rate = VenusInterestModel.utilization_rate(cash, borrows, reserves)
        borrow_rate_per_block = self.borrow_rate_per_block(cash, borrows, reserves)
        return borrow_rate_per_block * utilization_rate * (Decimal(1) - self.params.reserve_factor)


class VenusWhitePaperInterestModel(VenusInterestModel):

    def borrow_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:

        utilization_rate = VenusInterestModel.utilization_rate(cash, borrows, reserves)

        return utilization_rate * self.params.multiplier_per_block + \
               self.params.base_rate_per_block


class VenusJumpInterestModel(VenusInterestModel):

    def borrow_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:

        utilization_rate = VenusInterestModel.utilization_rate(cash, borrows, reserves)

        if utilization_rate <= self.params.kink:
            return utilization_rate * self.params.multiplier_per_block + \
                   self.params.base_rate_per_block
        else:
            normal_rate = self.params.kink * self.params.multiplier_per_block + self.params.base_rate_per_block
            excess_rate = (utilization_rate - self.params.kink) * self.params.jump_multiplier_per_block
            return normal_rate + excess_rate
