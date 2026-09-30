class ContactNormalizer:
    @staticmethod
    def normalize(records: list[dict]) -> dict[str, list[dict]]:
        normalized = []
        for r in records:
            props = r.get("properties", {})
            normalized.append({
                "id": str(r.get("id")),
                "email": props.get("email"),
                "firstname": props.get("firstname"),
                "lastname": props.get("lastname"),
                "phone": props.get("phone"),
                "createdate": props.get("createdate"),
                "lastmodifieddate": props.get("lastmodifieddate"),
                "raw_properties": props
            })
        return {"contacts": normalized}


class CompanyNormalizer:
    @staticmethod
    def normalize(records: list[dict]) -> dict[str, list[dict]]:
        normalized = []
        for r in records:
            props = r.get("properties", {})
            normalized.append({
                "id": str(r.get("id")),
                "name": props.get("name"),
                "domain": props.get("domain"),
                "industry": props.get("industry"),
                "city": props.get("city"),
                "state": props.get("state"),
                "createdate": props.get("createdate"),
                "raw_properties": props
            })
        return {"companies": normalized}


class DealNormalizer:
    @staticmethod
    def normalize(records: list[dict]) -> dict[str, list[dict]]:
        deals = []
        associations = []
        for r in records:
            deal_id = str(r.get("id"))
            props = r.get("properties", {})
            
            deals.append({
                "id": deal_id,
                "dealname": props.get("dealname"),
                "amount": props.get("amount"),
                "dealstage": props.get("dealstage"),
                "pipeline": props.get("pipeline"),
                "closedate": props.get("closedate"),
                "createdate": props.get("createdate"),
                "raw_properties": props
            })

            # Process associations if present
            assoc_data = r.get("associations", {})
            for assoc_type, assoc_body in assoc_data.items():
                for item in assoc_body.get("results", []):
                    associations.append({
                        "deal_id": deal_id,
                        "associated_type": assoc_type,
                        "associated_id": str(item.get("id"))
                    })

        return {
            "deals": deals,
            "deal_associations": associations
        }


class TicketNormalizer:
    @staticmethod
    def normalize(records: list[dict]) -> dict[str, list[dict]]:
        normalized = []
        for r in records:
            props = r.get("properties", {})
            normalized.append({
                "id": str(r.get("id")),
                "subject": props.get("hs_ticket_subject"),
                "content": props.get("content"),
                "status": props.get("hs_ticket_status"),
                "priority": props.get("hs_ticket_priority"),
                "createdate": props.get("createdate"),
                "raw_properties": props
            })
        return {"tickets": normalized}


class OwnerNormalizer:
    @staticmethod
    def normalize(records: list[dict]) -> dict[str, list[dict]]:
        normalized = []
        for r in records:
            normalized.append({
                "id": str(r.get("id")),
                "email": r.get("email"),
                "first_name": r.get("firstName"),
                "last_name": r.get("lastName"),
                "user_id": str(r.get("userId")) if r.get("userId") else None,
                "created_at": r.get("createdAt"),
                "updated_at": r.get("updatedAt"),
                "archived": r.get("archived", False)
            })
        return {"owners": normalized}


class NormalizationService:
    NORMALIZERS = {
        "contacts": ContactNormalizer,
        "companies": CompanyNormalizer,
        "deals": DealNormalizer,
        "tickets": TicketNormalizer,
        "owners": OwnerNormalizer,
    }

    @classmethod
    def normalize_object_data(cls, object_type: str, records: list[dict]) -> dict[str, list[dict]]:
        normalizer = cls.NORMALIZERS.get(object_type.lower())
        if not normalizer:
            raise ValueError(f"Unsupported object type for normalization: {object_type}")
        return normalizer.normalize(records)