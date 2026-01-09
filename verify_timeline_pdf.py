
def get_pdf_fig_height(phases_count):
    return max(4, phases_count * 1.0 + 2)

def verify_pdf_logic():
    print("--- PDF VERIFICATION START ---")
    
    # Case 1: Small (2 items)
    h_small = get_pdf_fig_height(2)
    # Expected: max(4, 2*1.0 + 2) = 4
    print(f"Small (2 items): Expected 4.0, Got {h_small}")
    if h_small == 4.0:
        print("PASS: Small Dataset.")
    else:
        print("FAIL: Small Dataset.")

    # Case 2: Large (20 items)
    h_large = get_pdf_fig_height(20)
    # Expected: max(4, 20*1.0 + 2) = 22.0
    print(f"Large (20 items): Expected 22.0, Got {h_large}")
    if h_large == 22.0:
        print("PASS: Large Dataset.")
    else:
        print("FAIL: Large Dataset.")

    print("--- PDF VERIFICATION END ---")

if __name__ == "__main__":
    verify_pdf_logic()
