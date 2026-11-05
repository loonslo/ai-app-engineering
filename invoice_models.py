# invoice_models.py
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class InvoiceItem(BaseModel):
    name: str = Field(min_length=1, description="消费明细名称")
    amount: Decimal = Field(gt=Decimal("0"), description="单项金额，必须大于 0")


class RawInvoiceInput(BaseModel):
    invoice_id: str = Field(min_length=1, description="发票唯一编号")
    currency: str = Field(default="CNY", description="币种标识")
    total_amount: Decimal = Field(gt=Decimal("0"), description="发票总金额，必须大于 0")
    items: list[InvoiceItem] = Field(min_length=1, description="消费条目列表，至少包含一项")

    @model_validator(mode="after")
    def verify_total_matches_items(self) -> "RawInvoiceInput":
        computed_sum = sum(item.amount for item in self.items)
        if computed_sum != self.total_amount:
            raise ValueError(
                f"发票 {self.invoice_id} 明细合计金额 ({computed_sum}) 与总金额 ({self.total_amount}) 不一致"
            )
        return self
