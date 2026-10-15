import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    TECHNICIAN = "technician"

    # Backward compatibility aliases for existing codebase & extendability
    CUSTOMER = "client"
    PROVIDER = "technician"
    ADMIN = "admin"


class TechnicianTrade(str, enum.Enum):
    PLUMBER = "plumber"
    ELECTRICIAN = "electrician"
    CARPENTER = "carpenter"
    HVAC = "hvac"
    CLEANER = "cleaner"
    PAINTER = "painter"
    HANDYMAN = "handyman"
    APPLIANCE_REPAIR = "appliance_repair"
    ROOFER = "roofer"
    OTHER = "other"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"


class JobStatus(str, enum.Enum):
    OPEN = "OPEN"
    BIDDING = "BIDDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTE = "DISPUTE"


class UrgencyLevel(str, enum.Enum):
    EMERGENCY = "EMERGENCY"
    THIS_WEEK = "THIS_WEEK"
    FLEXIBLE = "FLEXIBLE"


class BidStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"


class EscrowStatus(str, enum.Enum):
    HOLDING = "HOLDING"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"


class NotificationType(str, enum.Enum):
    NEW_JOB = "NEW_JOB"
    BID_RECEIVED = "BID_RECEIVED"
    BID_ACCEPTED = "BID_ACCEPTED"
    BID_REJECTED = "BID_REJECTED"
    JOB_ASSIGNED = "JOB_ASSIGNED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_CANCELLED = "JOB_CANCELLED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    REVIEW_RECEIVED = "REVIEW_RECEIVED"
    PAYMENT_RELEASED = "PAYMENT_RELEASED"
    SYSTEM_ALERT = "SYSTEM_ALERT"
