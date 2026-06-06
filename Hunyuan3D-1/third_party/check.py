from pathlib import Path


THIRD_PARTY_DIR = Path(__file__).resolve().parent


def check_bake_available(verbose=True):
    is_ok = (THIRD_PARTY_DIR / "weights" / "DUSt3R_ViTLarge_BaseDecoder_512_dpt" / "model.safetensors").exists()
    is_ok = is_ok and (THIRD_PARTY_DIR / "dust3r").exists()
    is_ok = is_ok and (THIRD_PARTY_DIR / "dust3r" / "dust3r").exists()
    is_ok = is_ok and (THIRD_PARTY_DIR / "dust3r" / "croco" / "models").exists()
    if verbose:
        if is_ok:
            print("Baking is available")
        else:
            print("Baking is unavailable, please download related files in README")
    return is_ok



if __name__ == "__main__":
    
    check_bake_available()
    
