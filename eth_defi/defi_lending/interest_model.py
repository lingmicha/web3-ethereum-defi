"""
 Compound Style Rates Calculation: Refer README.md
"""

from decimal import Decimal
from typing import NamedTuple


class InterestModelParameters(NamedTuple):
    reserve_factor: Decimal
    kink: Decimal
    base_rate_per_block: Decimal
    multiplier_per_block: Decimal
    jump_multiplier_per_block: Decimal

    def __eq__(self, other):
        # 大部分的参数已经在10e-7~10e-8量级，所以比较相等时，要用更小的误差范围
        return abs(self.reserve_factor - other.reserve_factor) < Decimal(10**-10) and \
               abs(self.kink - other.kink) < Decimal(10**-10) and \
               abs(self.base_rate_per_block - other.base_rate_per_block) < Decimal(10**-10) and \
                abs(self.multiplier_per_block - other.multiplier_per_block) < Decimal(10**-10) and \
                abs(self.jump_multiplier_per_block - other.jump_multiplier_per_block) < Decimal(10**-10)


class InterestModel:
    def __init__(self, params: InterestModelParameters):
        self.params = params

    @staticmethod
    def utilization_rate(cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:

        if borrows == Decimal(0):
            return Decimal(0)
        return Decimal(borrows / (borrows + cash - reserves))

    def borrow_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:
        pass

    def supply_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:
        utilization_rate = InterestModel.utilization_rate(cash, borrows, reserves)
        borrow_rate_per_block = self.borrow_rate_per_block(cash, borrows, reserves)
        return borrow_rate_per_block * utilization_rate * (Decimal(1) - self.params.reserve_factor)

    def minimum_borrow_rate_per_block(self) -> Decimal:
        pass

    def maximum_borrow_rate_per_block(self) -> Decimal:
        pass

    def minimum_supply_rate_per_block(self) -> Decimal:
        pass

    def maximum_supply_rate_per_block(self) -> Decimal:
        pass


class SimpleInterestModel(InterestModel):
    """简单的线性利率模型"""
    def borrow_rate_per_block(self, cash: Decimal, borrows: Decimal, reserves: Decimal) -> Decimal:

        utilization_rate = InterestModel.utilization_rate(cash, borrows, reserves)

        return utilization_rate * self.params.multiplier_per_block + \
               self.params.base_rate_per_block

    def minimum_borrow_rate_per_block(self) -> Decimal:
        return self.params.base_rate_per_block

    def maximum_borrow_rate_per_block(self):
        return self.params.base_rate_per_block + self.params.multiplier_per_block

    def minimum_supply_rate_per_block(self) -> Decimal:
        return Decimal(0)

    def maximum_supply_rate_per_block(self) -> Decimal:
        return (Decimal(1) - self.params.reserve_factor) * self.maximum_borrow_rate_per_block()


class JumpInterestModel(InterestModel):
    """分段线性的利率定价模型"""

    def borrow_rate_per_block(self, cash:Decimal, borrows:Decimal, reserves:Decimal) -> Decimal:

        utilization_rate = InterestModel.utilization_rate(cash, borrows, reserves)

        if utilization_rate <= self.params.kink:
            return utilization_rate * self.params.multiplier_per_block + \
                   self.params.base_rate_per_block
        else:
            normal_rate = self.params.kink * self.params.multiplier_per_block + self.params.base_rate_per_block
            excess_rate = (utilization_rate - self.params.kink) * self.params.jump_multiplier_per_block
            return normal_rate + excess_rate

    def minimum_borrow_rate_per_block(self) -> Decimal:
        return self.params.base_rate_per_block

    def maximum_borrow_rate_per_block(self):
        normal_rate = self.params.kink * self.params.multiplier_per_block + self.params.base_rate_per_block
        excess_rate = (Decimal(1) - self.params.kink) * self.params.jump_multiplier_per_block

        return normal_rate + excess_rate

    def minimum_supply_rate_per_block(self) -> Decimal:
        return Decimal(0)

    def maximum_supply_rate_per_block(self) -> Decimal:
        return (Decimal(1) - self.params.reserve_factor) * self.maximum_borrow_rate_per_block()
