import streamlit as st
from fpdf import FPDF
import io

st.set_page_config(
    page_title="TXT to PDF Converter",
    page_icon="📄",
    layout="centered"
)

class PDF(FPDF):
    def header(self):
        # Optional: Add a simple header
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, 'Generated via TXT to PDF Converter', 0, 1, 'C')

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def convert_txt_to_pdf(text_content):
    """
    Converts raw text string into a PDF byte stream.
    """
    pdf = PDF()
    pdf.add_page()
    pdf.set_margins(left=15, top=20, right=15)
    
    # Set Font: Helvetica is standard and legible
    pdf.set_font("Helvetica", size=11)
    
    # Use multi_cell for automatic line wrapping
    # w=0 means the cell extends to the right margin
    pdf.multi_cell(w=0, h=10, txt=text_content)
    
    # Return the PDF as bytes
    return pdf.output()

def main():
    st.title("📄 Text to PDF Converter")
    st.markdown("""
    Upload a plain text file (`.txt`) and convert it into a clean, formatted PDF document instantly.
    """)

    uploaded_file = st.file_uploader("Choose a .txt file", type=["txt"])

    if uploaded_file is not None:
        try:
            # Read file with utf-8 to handle special characters safely
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_data = stringio.read()

            # UI Sections
            st.divider()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📝 Text Preview")
                with st.container(border=True):
                    # Show a snippet or the whole text in a scrollable area
                    st.text_area("Content", value=text_data, height=300, disabled=True)

            with col2:
                st.subheader("⚙️ Actions")
                if st.button("🚀 Generate PDF", use_container_width=True):
                    with st.spinner("Creating your PDF..."):
                        pdf_bytes = convert_txt_to_pdf(text_data)
                        
                        st.success("✅ PDF successfully generated!")
                        
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_bytes,
                            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.balloons()
                        
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("Please ensure the file is a valid UTF-8 encoded .txt file.")

if __name__ == "__main__":
    main()