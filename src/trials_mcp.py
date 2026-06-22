
import requests
from typing import Optional

CTGOV_BASE = "https://clinicaltrials.gov/api/v2"

def search_trials(condition, intervention=None, phase=None, status="RECRUITING", max_results=10):
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": max_results,
        "format": "json"
    }
    if intervention:
        params["query.intr"] = intervention
    if phase:
        params["filter.phase"] = phase

    try:
        response = requests.get(f"{CTGOV_BASE}/studies", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        studies = data.get("studies", [])
        results = []
        for study in studies:
            proto = study.get("protocolSection", {})
            id_mod = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            desc_mod = proto.get("descriptionModule", {})
            elig_mod = proto.get("eligibilityModule", {})
            sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
            locations = proto.get("contactsLocationsModule", {}).get("locations", [])
            location_str = "Not specified"
            if locations:
                loc = locations[0]
                parts = [loc.get("city",""), loc.get("state",""), loc.get("country","")]
                location_str = ", ".join(p for p in parts if p)
            results.append({
                "nct_id": id_mod.get("nctId",""),
                "title": id_mod.get("briefTitle",""),
                "phase": status_mod.get("phase","Not specified"),
                "status": status_mod.get("overallStatus",""),
                "summary": desc_mod.get("briefSummary","")[:500],
                "eligibility": elig_mod.get("eligibilityCriteria","")[:800],
                "sponsor": sponsor_mod.get("leadSponsor",{}).get("name",""),
                "location": location_str,
                "min_age": elig_mod.get("minimumAge",""),
                "max_age": elig_mod.get("maximumAge",""),
                "sex": elig_mod.get("sex","ALL"),
                "url": f"https://clinicaltrials.gov/study/{id_mod.get('nctId','')}"
            })
        return {"success": True, "total_found": data.get("totalCount", len(results)), "trials": results}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "trials": []}

def get_trial_details(nct_id):
    try:
        response = requests.get(f"{CTGOV_BASE}/studies/{nct_id}", params={"format": "json"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        proto = data.get("protocolSection", {})
        id_mod = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        desc_mod = proto.get("descriptionModule", {})
        elig_mod = proto.get("eligibilityModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        locations = proto.get("contactsLocationsModule", {}).get("locations", [])
        location_list = []
        for loc in locations[:5]:
            parts = [loc.get("facility",""), loc.get("city",""), loc.get("state",""), loc.get("country","")]
            location_list.append(", ".join(p for p in parts if p))
        return {
            "success": True,
            "nct_id": nct_id,
            "title": id_mod.get("briefTitle",""),
            "phase": status_mod.get("phase",""),
            "status": status_mod.get("overallStatus",""),
            "summary": desc_mod.get("briefSummary",""),
            "eligibility": elig_mod.get("eligibilityCriteria",""),
            "min_age": elig_mod.get("minimumAge",""),
            "max_age": elig_mod.get("maximumAge",""),
            "sex": elig_mod.get("sex",""),
            "sponsor": sponsor_mod.get("leadSponsor",{}).get("name",""),
            "locations": location_list,
            "url": f"https://clinicaltrials.gov/study/{nct_id}"
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def check_eligibility(patient_profile, trial):
    reasons = []
    score = 0
    total = 0
    patient_age = patient_profile.get("age")
    min_age = trial.get("min_age","").replace(" Years","").strip()
    if patient_age and min_age:
        total += 1
        try:
            if int(patient_age) >= int(min_age):
                score += 1
                reasons.append(f"Age {patient_age} meets minimum age {min_age}")
            else:
                reasons.append(f"Age {patient_age} below minimum age {min_age}")
        except ValueError:
            reasons.append("Could not verify age requirement")
    patient_sex = patient_profile.get("sex","").upper()
    trial_sex = trial.get("sex","ALL").upper()
    if trial_sex and trial_sex != "ALL":
        total += 1
        if patient_sex == trial_sex:
            score += 1
            reasons.append(f"Sex matches trial requirement")
        else:
            reasons.append(f"Sex mismatch: patient {patient_sex}, trial requires {trial_sex}")
    condition = patient_profile.get("condition","").lower()
    if condition:
        total += 1
        if condition in trial.get("eligibility","").lower() or condition in trial.get("title","").lower():
            score += 1
            reasons.append(f"Condition relevant to trial")
        else:
            reasons.append(f"Condition not explicitly mentioned - manual review needed")
    match_pct = round((score/total*100) if total > 0 else 0)
    return {
        "nct_id": trial.get("nct_id",""),
        "title": trial.get("title",""),
        "match_score": match_pct,
        "reasons": reasons,
        "recommendation": "Strong match" if match_pct >= 70 else "Partial match" if match_pct >= 40 else "Low match",
        "url": trial.get("url","")
    }

if __name__ == "__main__":
    import requests
    print("Testing ClinicalTrials.gov API...")
    results = search_trials("breast cancer", max_results=3)
    if results["success"]:
        print(f"Found {results['total_found']} trials")
        for t in results["trials"]:
            print(f"- {t['nct_id']}: {t['title'][:60]}")
    else:
        print(f"Error: {results['error']}")
