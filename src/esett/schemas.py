from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class LoadProfileDataPoint(BaseModel):
    time: datetime
    mba: str
    mga_code: str | None
    mga_name: str | None
    quantity: float | None


class ProductionDataPoint(BaseModel):
    time: datetime
    mba: str
    total: float | None
    hydro: float | None
    wind: float | None
    wind_offshore: float | None
    solar: float | None
    nuclear: float | None
    thermal: float | None
    energy_storage: float | None
    other: float | None


class ConsumptionDataPoint(BaseModel):
    time: datetime
    mba: str
    total: float | None
    metered: float | None
    profiled: float | None
    flex: float | None


class ImbalancePriceDataPoint(BaseModel):
    time: datetime
    mba: str
    up_reg_price: float | None
    down_reg_price: float | None
    imbl_purchase_price: float | None
    imbl_sales_price: float | None
    imbl_spot_difference_price: float | None
    incentivising_component: float | None
    main_dir_reg_power_per_mba: float | None
    value_of_avoided_activation: float | None
    up_reg_price_frr_a: float | None
    down_reg_price_frr_a: float | None


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
    cached: bool


# Backward compat alias
LoadProfileResponse = PaginatedResponse[LoadProfileDataPoint]
