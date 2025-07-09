
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './App.css'
import Hero from './components/Hero'
import { Toaster } from 'react-hot-toast';

function App() {

  return (
    <Router>
      <Toaster />
      <div className="min-h-screen bg-gray-100">
        <Hero />
        
      </div>
    </Router>
  )
}

export default App
