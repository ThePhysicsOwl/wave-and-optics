# PHY-104: Wave and Optics

Welcome to the **Wave and Optics** repository! This repository serves as the central digital hub for all course materials, interactive physics simulations, lecture slides, problem sets, and quizzes designed to help students master oscillatory mechanics, wave phenomena, and optics.

---

## 📚 Course Resources

This repository will expand as the course progresses. Here is how the materials are organized:

### 1. Interactive Simulations
Located in topic-specific directories (e.g., `periodic motion/`), these folders contain high-precision Python physics simulators. 
* **Featured: Harmonic Oscillator Lab** (Real-time modeling of springs, pendulums, and phase space).
  
  * **For Students:** Go to the [Releases](../../releases/latest) tab and download the compiled `.rar` files to run the labs instantly without installing Python.
  * **For Developers:** Navigate to the simulation's folder and double-click `setup_and_run.bat` (Windows) or execute `./setup_and_run.sh` (Mac/Linux) to run the raw Python code.

### 📽️ 2. Lecture Slides & Notes
All lecture presentations (including our custom LaTeX Beamer slides) and Tufte-style textbook chapters are organized by topic. These provide the rigorous mathematical and historical foundation for the concepts demonstrated in the simulations.

### 📝 3. Problem Sets (Psets)
Weekly problem sets are provided in PDF format. These are designed to test your analytical understanding of the concepts.

### 🧠 4. Quizzes
Short conceptual quizzes and targeted mathematical assessments to test your grasp of the material before major exams. 

---

## 📥 How to Use This Repository

**For Students:**
If you are just looking to access homework PDFs, review slides, or download the simulation software, you do not need to use Git or the command line! 
* You can browse the folders directly here on GitHub to view and download PDFs.
* You can visit the **[Releases](../../releases/latest)** page to download the ready-to-run `.exe` applications.

**For Developers & Teaching Assistants:**
If you want to run the raw Python code, tweak the SciPy differential equation solvers yourself:

```bash
# Clone the repository
git clone https://github.com/ThePhysicsOwl/wave-and-optics.git

# Navigate to the specific project you want to explore
cd "wave-and-optics/TOPICNAME"

# Run the automated virtual environment setup script (for Python apps)
./setup_and_run.bat   # Windows
./setup_and_run.sh    # Mac/Linux
```

---
*Developed and maintained by ThePhysicsOwl & Japn07.*
