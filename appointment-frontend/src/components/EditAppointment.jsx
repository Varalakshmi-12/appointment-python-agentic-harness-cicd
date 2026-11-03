import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import API from "../api";
import { Link } from "react-router-dom";

export default function EditAppointment() {
  const { id } = useParams();
  const [form, setForm] = useState(null);

  useEffect(() => {
    API.get(`/appointments/${id}`).then((res) => setForm(res.data));
  }, [id]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleUpdate = async () => {
    await API.put(`/appointments/${id}`, form);
    alert("Updated!");
  };

  const handleDelete = async () => {
    await API.delete(`/appointments/${id}`);
    alert("Deleted!");
  };

  if (!form) return <p>Loading...</p>;

  return (
    <div>
      <h2>Edit Appointment</h2>
      <input name="patient_name" value={form.patient_name} onChange={handleChange} />
      <input name="patient_phone" value={form.patient_phone} onChange={handleChange} />
      <select name="provider_name" value={form.provider_name} onChange={handleChange}>
        <option value="">Select Provider</option>
        <option value="Dr. Smith">Dr. Smith</option>
        <option value="Dr. Johnson">Dr. Johnson</option>
      </select>
      <input type="email" placeholder="Enter patient email"
           name="patient_email"
           value={form.patient_email}
           onChange={handleChange}
           required
      />

      <input type="datetime-local" name="appointment_time" value={form.appointment_time} onChange={handleChange} />

      <p>
        Status: {form.status}
        {" "}(change status from the appointment list)
      </p>

      <button onClick={handleUpdate}>Update</button>
      <button onClick={handleDelete} style={{ color: "red" }}>Delete</button>
      <Link to="/" style={{ marginLeft: "10px" }}>
        Home
      </Link>
    </div>
  );
}