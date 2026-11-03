import { useState } from "react";
import API from "../api";
import { Link } from "react-router-dom";

export default function AppointmentForm() {
  const [form, setForm] = useState({
    patient_name: "",
    patient_phone: "",
    provider_name: "",
    patient_email: "",
    appointment_time: ""
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await API.post("/appointments", form);
    alert("Appointment created!");
  };

  return (
    <div>
      <h2>Create Appointment</h2>
      <form onSubmit={handleSubmit}>
        <input name="patient_name" placeholder="Patient Name" onChange={handleChange} />
        <input name="patient_phone" placeholder="Phone" onChange={handleChange} />
        <select name="provider_name" placeholder="Provider" onChange={handleChange} >
          <option value="">Select Provider</option>
          <option value="Dr. Smith">Dr. Smith</option>
          <option value="Dr. Johnson">Dr. Johnson</option>
        </select>
        <input type="email" placeholder="Enter patient email"
           name="patient_email"
           onChange={handleChange}
           required
        />
        <input type="datetime-local" name="appointment_time" onChange={handleChange} />
        <button type="submit">Create</button>
        <Link to="/" style={{ marginLeft: "10px" }}>
          Home
        </Link>
      </form>
    </div>
  );
}