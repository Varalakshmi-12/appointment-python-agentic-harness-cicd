import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppointmentForm from "./components/AppointmentForm";
import AppointmentList from "./components/AppointmentList";
import EditAppointment from "./components/EditAppointment";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        
        <Route path="/" element={<AppointmentList />} />
        <Route path="/new" element={<AppointmentForm />} />
        <Route path="/edit/:id" element={<EditAppointment />} />
      </Routes>
    </BrowserRouter>
  );
}