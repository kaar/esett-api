from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LoadProfile(Base):
    """eSett load profile data cached from /EXP18/LoadProfile.

    Composite PK: (time, mba, mga_code).
    When eSett returns mgaCode=null (no mga filter), we store mga_code=""
    as a sentinel to satisfy the non-nullable PK constraint.
    """

    __tablename__ = "load_profile"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    mba: Mapped[str] = mapped_column(String, primary_key=True)
    mga_code: Mapped[str] = mapped_column(String, primary_key=True, default="")
    mga_name: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)


class Production(Base):
    """eSett hourly production by source from /EXP16/Volumes.

    Composite PK: (time, mba).
    """

    __tablename__ = "production"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    mba: Mapped[str] = mapped_column(String, primary_key=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    hydro: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_offshore: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar: Mapped[float | None] = mapped_column(Float, nullable=True)
    nuclear: Mapped[float | None] = mapped_column(Float, nullable=True)
    thermal: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_storage: Mapped[float | None] = mapped_column(Float, nullable=True)
    other: Mapped[float | None] = mapped_column(Float, nullable=True)


class Consumption(Base):
    """eSett hourly consumption by measurement type from /EXP15/Consumption.

    Composite PK: (time, mba).
    """

    __tablename__ = "consumption"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    mba: Mapped[str] = mapped_column(String, primary_key=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    metered: Mapped[float | None] = mapped_column(Float, nullable=True)
    profiled: Mapped[float | None] = mapped_column(Float, nullable=True)
    flex: Mapped[float | None] = mapped_column(Float, nullable=True)


class ImbalancePrice(Base):
    """eSett hourly imbalance prices from /EXP14/Prices.

    Composite PK: (time, mba).
    """

    __tablename__ = "imbalance_price"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    mba: Mapped[str] = mapped_column(String, primary_key=True)
    up_reg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    down_reg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    imbl_purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    imbl_sales_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    imbl_spot_difference_price: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    incentivising_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    main_dir_reg_power_per_mba: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    value_of_avoided_activation: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    up_reg_price_frr_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    down_reg_price_frr_a: Mapped[float | None] = mapped_column(Float, nullable=True)
