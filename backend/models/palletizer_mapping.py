from sqlalchemy import Column, Integer, String, Float, DateTime, func
from database import Base

class PalletizerMapping(Base):
    __tablename__ = "palletizer_mapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), unique=True, nullable=False)
    palletizer = Column(String(50), nullable=False)

    # ✅ A2: the SCADA counter tag for this line. Replaced the hardcoded
    # PL_TO_SCADA map, so adding a line no longer needs a code change.
    scada_tag = Column(String(50), nullable=True)

    # ✅ A2: correctly-named columns. The three below them are transposed —
    # `bag_size_kg` has always held the bags-per-pallet multiplier (CKL1 is 32
    # bags of 45 kg, not a 32 kg bag) and `bags_per_pallet` sits unused at 1.
    # The backend reads these two; the old three are still written because
    # PalletizerMapping.tsx and lib/api.ts require them. A6 switches the screen,
    # then a later cleanup drops the old ones.
    bags_per_pallet_actual = Column(Float, nullable=True)  # the delta multiplier
    bag_weight_kg = Column(Float, nullable=True)           # weight of one bag

    # DEPRECATED (A2) - misnamed, kept for the current frontend contract.
    bag_size_kg = Column(Float, nullable=False)      # actually bags per pallet
    bags_per_pallet = Column(Float, nullable=False)  # actually unused, 1 everywhere
    kg_per_pallet = Column(Float, nullable=False)    # actually the bag weight

    # Description field for additional info about the mapping
    description = Column(String(255), nullable=True)

    def multiplier(self) -> float:
        """
        Bags produced per unit of SCADA delta.

        Prefers the correctly-named column, falling back to the legacy one so a
        row written by an older client still converts.
        """
        for value in (self.bags_per_pallet_actual, self.bag_size_kg):
            try:
                number = float(value or 0)
            except (TypeError, ValueError):
                continue
            if number > 1:
                return number
        return 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "palletizer": self.palletizer,
            "scada_tag": self.scada_tag,
            "bags_per_pallet_actual": float(self.bags_per_pallet_actual or 0),
            "bag_weight_kg": float(self.bag_weight_kg or 0),
            # Deprecated aliases - the screen still reads these.
            "bag_size_kg": float(self.bag_size_kg or 0),
            "bags_per_pallet": int(self.bags_per_pallet or 0),
            "kg_per_pallet": float(self.kg_per_pallet or 0),
            "description": self.description,
        }

    # Optional: Only include if column exists in database
    # created_at = Column(DateTime, server_default=func.now())
    # updated_at = Column(DateTime, onupdate=func.now())
