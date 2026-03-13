import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Key, Check, ArrowRight, ExternalLink } from 'lucide-react';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [apiKey, setApiKey] = useState('');
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const storedKey = localStorage.getItem('gemini_api_key') || '';
      setApiKey(storedKey);
      setIsSaved(false);
    }
  }, [isOpen]);

  const handleSave = () => {
    if (apiKey.trim()) {
      localStorage.setItem('gemini_api_key', apiKey.trim());
      sessionStorage.removeItem('skip_api_key');
    } else {
      localStorage.removeItem('gemini_api_key');
    }
    setIsSaved(true);
    setTimeout(() => {
      onClose();
    }, 1000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
           className="modal-overlay"
           initial={{ opacity: 0 }}
           animate={{ opacity: 1 }}
           exit={{ opacity: 0 }}
        >
          <motion.div
            className="modal-container"
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
          >
            {/* Left Side - Instructions */}
            <div className="modal-left">
              <div className="modal-header">
                <div className="modal-icon-wrap">
                  <Key size={24} />
                </div>
                <h2 className="modal-title">Setup Required</h2>
              </div>
              
              <p className="modal-description">
                CareerForge uses Google's latest Gemini AI models to provide personalized career guidance and live mock interviews.
              </p>

              <div className="setup-steps">
                <h3 className="setup-steps-title">How to get your API Key</h3>
                
                <div className="step-list">
                  <div className="setup-step">
                    <div className="step-number">1</div>
                    <div className="step-content">
                      <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="step-link">
                        Open Google AI Studio <ExternalLink size={14} style={{ marginLeft: 6 }} />
                      </a>
                      <p className="step-desc">Sign in with your Google account.</p>
                    </div>
                  </div>

                  <div className="setup-step">
                    <div className="step-number">2</div>
                    <div className="step-content">
                      <p>Click "Create API key"</p>
                      <p className="step-desc">Generate a new key in a new or existing project.</p>
                    </div>
                  </div>

                  <div className="setup-step">
                    <div className="step-number">3</div>
                    <div className="step-content">
                      <p>Copy and Paste</p>
                      <p className="step-desc">Paste your key in the field here to continue.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Side - Input */}
            <div className="modal-right">
              <button
                onClick={onClose}
                className="modal-close-btn"
              >
                <X size={20} />
              </button>

              <div className="modal-inner-content">
                <h3 className="modal-right-title">Enter API Key to Continue</h3>
                <p className="modal-right-desc">Your key is stored locally and never saved on our servers.</p>

                <div className="input-group">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="AIzaSy..."
                    className="modal-input"
                  />
                  <Key size={20} className="input-icon" />
                </div>

                <button
                  onClick={handleSave}
                  disabled={!apiKey.trim()}
                  className={`modal-save-btn ${
                    isSaved
                      ? 'saved'
                      : apiKey.trim()
                      ? 'active'
                      : 'disabled'
                  }`}
                >
                  {isSaved ? (
                    <>
                      <Check size={20} />
                      <span>Ready to Go!</span>
                    </>
                  ) : (
                    <>
                      <span>Continue to Forge</span>
                      <ArrowRight size={20} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
