from pydantic import BaseModel, Field, computed_field
from functools import cached_property
from typing import List, Dict
import random
import matplotlib.pyplot as plt

class MarketAction(BaseModel):
    price: float = Field(..., description="Price of the order")
    quantity: int = Field(default=1, ge=1, description="Quantity of the order")

class Bid(MarketAction):
    is_buyer: bool = True

class Ask(MarketAction):
    is_buyer: bool = False


class Trade(BaseModel):
    trade_id: int = Field(..., description="Unique identifier for the trade")
    buyer_id: str = Field(..., description="ID of the buyer")
    seller_id: str = Field(..., description="ID of the seller")
    price: float = Field(..., description="The price at which the trade was executed")
    quantity: int = Field(default=1, description="The quantity traded")
    good_name: str = Field(default="consumption_good", description="The name of the good traded")

class Good(BaseModel):
    name: str
    quantity: float

class Basket(BaseModel):
    cash: float
    goods: List[Good]


    @computed_field
    @cached_property
    def goods_dict(self) -> Dict[str, float]:
        return {good.name: good.quantity for good in self.goods}



    def update_good(self, name: str, quantity: float):
        for good in self.goods:
            if good.name == name:
                good.quantity = quantity
                return
        self.goods.append(Good(name=name, quantity=quantity))

    def get_good_quantity(self, name: str) -> float:
        return next((good.quantity for good in self.goods if good.name == name), 0)
    
class Endowment(BaseModel):
    initial_basket: Basket
    trades: List[Trade] = Field(default_factory=list)
    agent_id: str

    @computed_field
    @property
    def current_basket(self) -> Basket:
        current_cash = self.initial_basket.cash
        current_goods = {good.name: good.quantity for good in self.initial_basket.goods}

        for trade in self.trades:
            if trade.buyer_id == self.agent_id:
                current_cash -= trade.price * trade.quantity
                current_goods[trade.good_name] = current_goods.get(trade.good_name, 0) + trade.quantity
            elif trade.seller_id == self.agent_id:
                current_cash += trade.price * trade.quantity
                current_goods[trade.good_name] = current_goods.get(trade.good_name, 0) - trade.quantity

        return Basket(
            cash=current_cash,
            goods=[Good(name=name, quantity=quantity) for name, quantity in current_goods.items()]
        )

    def add_trade(self, trade: Trade):
        self.trades.append(trade)
        # Clear the cached property to ensure it's recalculated
        if 'current_basket' in self.__dict__:
            del self.__dict__['current_basket']



class PreferenceSchedule(BaseModel):
    num_units: int = Field(..., description="Number of units")
    base_value: float = Field(..., description="Base value for the first unit")
    noise_factor: float = Field(default=0.1, description="Noise factor for value generation")
    is_buyer: bool = Field(default=True, description="Whether the agent is a buyer")

    @computed_field
    @cached_property
    def values(self) -> Dict[int, float]:
        raise NotImplementedError("Subclasses must implement this method")

    @computed_field
    @cached_property
    def initial_endowment(self) -> float:
        raise NotImplementedError("Subclasses must implement this method")

    def get_value(self, quantity: int) -> float:
        return self.values.get(quantity, 0.0)

    def plot_schedule(self, block=False):
        quantities = list(self.values.keys())
        values = list(self.values.values())
        
        plt.figure(figsize=(10, 6))
        plt.plot(quantities, values, marker='o')
        plt.title(f"{'Demand' if isinstance(self, BuyerPreferenceSchedule) else 'Supply'} Schedule")
        plt.xlabel("Quantity")
        plt.ylabel("Value/Cost")
        plt.grid(True)
        plt.show(block=block)

class BuyerPreferenceSchedule(PreferenceSchedule):
    endowment_factor: float = Field(default=1.2, description="Factor to calculate initial endowment")
    is_buyer: bool = Field(default=True, description="Whether the agent is a buyer")

    @computed_field
    @cached_property
    def values(self) -> Dict[int, float]:
        values = {}
        current_value = self.base_value
        for i in range(1, self.num_units + 1):
            noise = random.uniform(-self.noise_factor, self.noise_factor) * current_value
            new_value = max(1, current_value + noise)  # Ensure no zero values
            if i > 1:
                new_value = min(new_value, values[i-1])  # Ensure monotonicity
            values[i] = new_value
            current_value *= random.uniform(0.95, 1.0)
        return values

    @computed_field
    @cached_property
    def initial_endowment(self) -> float:
        return sum(self.values.values()) * self.endowment_factor

class SellerPreferenceSchedule(PreferenceSchedule):
    is_buyer: bool = Field(default=False, description="Whether the agent is a buyer")
    @computed_field
    @cached_property
    def values(self) -> Dict[int, float]:
        values = {}
        current_value = self.base_value
        for i in range(1, self.num_units + 1):
            noise = random.uniform(-self.noise_factor, self.noise_factor) * current_value
            new_value = max(1, current_value + noise)  # Ensure no zero values
            if i > 1:
                new_value = max(new_value, values[i-1])  # Ensure monotonicity
            values[i] = new_value
            current_value *= random.uniform(1.0, 1.05)
        return values

    @computed_field
    @cached_property
    def initial_endowment(self) -> float:
        return sum(self.values.values())