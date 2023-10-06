CONFIG = {
    "data-tracker": {
        "obj": "object_75",
        "view": "view_1653",
        "fields": {
            "id": "id",
            "atd_activity_id": "field_1051",
            "emi_id": "field_1868",
            "sr_number": "field_1232",
            "issue_status_code_snapshot": "field_1874",
            "esb_status": "field_1860",
            "activity_datetime": "field_1054",
            "activity_details": "field_1055",
            "activity_name": "field_1053",
            "csr_activity_id": "field_4583",
            "csr_activity_code": "field_4582",
        },
        # This dict maps activity names in the AMD or Signs/Markings Data Tracker to activity
        # codes used by the CSR system. Here are the rules:
        # - If an activity used in Knack is not in this dict, an error will be thrown.
        # - If an activity name is in the dict with a value of `None`, the activity will
        # be **ignored** and updated as "DO NOT SEND" in Knack
        "activity_codes": {
            "Identify Asset": "IDENASSE",
            "Dispatch Technician": "DISPTECH",
            "Close Issue (Resolved)": "CLOIS001",
            "Adjust Timing": "ADJUTIMI",
            "Complete Repairs": "REPACOMP",
            "Assign to Signal Request Review": "ASSIRERE",
            "Assign to Signal Engineering": "ASTOSIEN",
            "Assign to TMC": "RETOMOMC",
            "Monitor in School Zone Beacon System": "MONISSRE",
            "Monitor Situation on CCTV": "MONISSRE",
            "311 Feedback": "311FEEDB",
            "Monitor Situation in KITS": "MONISSRE",
            "Close Issue (Duplicate)": "CLOIS001",
            "Remote Monitor Reset - Successful": "REMORESU",
            "Remote Monitor Reset - Unsuccessful": "REMOR001",
            "Other": None,
            "Storm-Related": None,
            "Adjust Video Detection": "ADJVIDDE",
            "Attach Image": None,
            "Post Tweet": None,
            "Update DMS": None,
            "Send Email": None,
            "Coordinate Internally/Externally": "COORINTE",
        },
    },
    "signs-markings": {
        "obj": "object_173",
        "view": "view_3052",
        "fields": {
            "id": "id",
            "atd_activity_id": "field_3143",
            "emi_id": "field_3163",
            "sr_number": "field_3154",
            "issue_status_code_snapshot": "field_3160",
            "esb_status": "field_3164",
            "activity_datetime": "field_3145",
            "activity_details": "field_3147",
            "activity_name": "field_3144",
            "csr_activity_id": "field_4321",
            "csr_activity_code": "field_4322",
        },
        # This dict maps activity names in the AMD or Signs/Markings Data Tracker to activity
        # codes used by the CSR system. Here are the rules:
        # - If an activity used in Knack is not in this dict, an error will be thrown.
        # - If an activity name is in the dict with a value of `None`, the activity will
        # be **ignored** and updated as "DO NOT SEND" in Knack
        "activity_codes": {
            "Conduct Investigation": "TMCONINV",
            "Contact Citizen": "CONTACT",
            "Dispatch Technician/Crew": "DISPATC2",
            "Repair/Replace": "TRREPSGN",
            "Attach Image": None,
            "Send Email": "CONTACT",
            "Close Issue (Duplicate)": "CLOIS001",
            "Close Issue (Resolved)": "CLOIS001",
            "311 Feedback": "311FEEDB",
            "Other": None,
        },
    },
}
