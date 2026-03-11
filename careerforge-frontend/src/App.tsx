import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import ChatSession from './pages/ChatSession';
import LiveSession from './pages/LiveSession';
import ReportPage from './pages/ReportPage';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/session/:id" element={<ChatSession />} />
        <Route path="/live/:id" element={<LiveSession />} />
        <Route path="/report/:id" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  );
}
