import React, { useRef } from "react";
import { Button, Paper, TableContainer } from "@mui/material";
import UploadIcon from '@mui/icons-material/Upload';
import DownloadIcon from "@mui/icons-material/Download";
import { API_BASE } from '../config';


const LandingPage = () => {
    const fileInputRef = useRef(null);

    const handleExport = () => {
        // Exports database as ZIP containing raw .sqlite3 + CSV files for each table
        window.location.href = `${API_BASE}/export_sqlite/?full=1`;
    };

    const handleImportClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleImportChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        const validTypes = [".sqlite3"];
        const fileExtension = file.name.split(".").pop();
        if (!validTypes.includes(`.${fileExtension}`)) {
            alert("Invalid file type. Please select a .sqlite3 file.");
            return;
        }

        const formData = new FormData();
        formData.append("sqlite_file", file);

        try {
            const response = await fetch(`${API_BASE}/import_sqlite/`, {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                alert("Database imported successfully!");
                window.location.reload();
            } else {
                alert("Failed to import database.");
            }
        } catch (error) {
            console.error("Error during import:", error);
            alert("Error during import.");
        }
    };

    return (
        <div>
            <div
                style={{
                    textAlign: "center",
                    marginTop: "40px",
                    marginBottom: "40px",
                }}
            >
                <img 
                    src="/static/bmintyFull.png" 
                    alt="bMinty" 
                    style={{
                        maxWidth: "50%",
                        height: "auto",
                        maxHeight: "600px"
                    }}
                />
            </div>

            <TableContainer
                component={Paper}
                sx={{
                    width: "80%",
                    margin: "auto",
                    mt: 3,
                    boxShadow: 3,
                    position: "relative",
                }}
            >
                {/* Table content would go here */}
            </TableContainer>

            {/* Navigation Buttons */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "center",
                    gap: "20px",
                    marginTop: "40px",
                    marginBottom: "60px",
                    width: "100%",
                }}
            >
                <Button
                    variant="contained"
                    size="large"
                    onClick={() => (window.location.href = "/explore/")}
                    sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: "1rem",
                        textTransform: "none",
                        backgroundColor: "#388e3c",
                        '&:hover': { backgroundColor: '#2e7031' },
                    }}
                >
                    Explore Database
                </Button>
                <Button
                    variant="contained"
                    size="large"
                    onClick={() => (window.location.href = "/graph/")}
                    sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: "1rem",
                        textTransform: "none",
                        backgroundColor: "#388e3c",
                        '&:hover': { backgroundColor: '#2e7031' },
                    }}
                >
                    Visualize Database
                </Button>
                <Button
                    variant="contained"
                    size="large"
                    onClick={() => window.open("http://127.0.0.1:8000/swagger/", "_blank", "noopener,noreferrer")}
                    sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: "1rem",
                        textTransform: "none",
                        backgroundColor: "#388e3c",
                        '&:hover': { backgroundColor: '#2e7031' },
                    }}
                >
                    Explore API
                </Button>                
            </div>

            {/* Hidden file input for SQLite import */}
            <input
                ref={fileInputRef}
                type="file"
                accept=".sqlite3"
                style={{ display: "none" }}
                onChange={handleImportChange}
            />

            {/* Bottom-fixed Import/Export bar */}
            <div
                style={{
                    position: "fixed",
                    bottom: 0,
                    left: 0,
                    right: 0,
                    backgroundColor: "#f5f5f5",
                    padding: "10px 20px",
                    display: "flex",
                    justifyContent: "center",
                    gap: "20px",
                    boxShadow: "0 -2px 8px rgba(0, 0, 0, 0.1)",
                    zIndex: 1000,
                }}
            >
                <Button
                    variant="contained"
                    size="large"
                    startIcon={<DownloadIcon />}
                    onClick={handleExport}
                    sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: "1rem",
                        textTransform: "none",
                        backgroundColor: "#388e3c",
                        '&:hover': { backgroundColor: '#2e7031' },
                    }}
                >
                    Export Database
                </Button>
                <Button
                    variant="contained"
                    size="large"
                    startIcon={<UploadIcon />}
                    onClick={handleImportClick}
                    sx={{
                        px: 4,
                        py: 1.5,
                        fontSize: "1rem",
                        textTransform: "none",
                        backgroundColor: "#388e3c",
                        '&:hover': { backgroundColor: '#2e7031' },
                    }}
                >
                    Import Database
                </Button>
            </div>

        </div>
    );
};

export default LandingPage;
