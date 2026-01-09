
def get_pdf_fig_height(phases_count):
    return max(3.0, phases_count * 0.4 + 1.5)

def verify_pdf_logic():
    print("--- PDF VERIFICATION START ---")
    
    # Case 1: Small (2 items)
    h_small = get_pdf_fig_height(2)
    # Expected: max(3.0, 2*0.4 + 1.5) = 3.0
    print(f"Small (2 items): Expected 3.0, Got {h_small}")
    if h_small == 3.0:
        print("PASS: Small Dataset.")
    else:
        print("FAIL: Small Dataset.")

    # Case 2: Large (20 items)
    h_large = get_pdf_fig_height(20)
    # Expected: max(3.0, 20*0.4 + 1.5) = 9.5
    print(f"Large (20 items): Expected 9.5, Got {h_large}")
    if h_large == 9.5:
        print("PASS: Large Dataset.")
    else:
        print("FAIL: Large Dataset.")

    print("--- PDF VERIFICATION END ---")

if __name__ == "__main__":
    verify_pdf_logic()
