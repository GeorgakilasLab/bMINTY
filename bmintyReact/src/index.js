import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import reportWebVitals from './reportWebVitals';
import ExplorePage from './pages/ExplorePage';
import StudyAssayGraph from './components/StudyAssayGraph';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <BrowserRouter>
        <Routes>
            {/* Explore page is now the main page */}
            <Route path="/" element={<ExplorePage />} />

            {/* Landing page route */}
            <Route path="/landing/" element={<LandingPage />} />

            {/* Visual graph route */}
            <Route path="/graph/" element={<StudyAssayGraph />} />
  
        </Routes>
    </BrowserRouter>
);

reportWebVitals();
