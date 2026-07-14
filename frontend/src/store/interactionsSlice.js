import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const fetchInteractions = createAsyncThunk(
  'interactions/fetchAll',
  async (hcpId) => {
    const { data } = await api.get('/interactions/', { params: hcpId ? { hcp_id: hcpId } : {} })
    return data
  }
)

export const createInteraction = createAsyncThunk(
  'interactions/create',
  async (payload) => {
    const { data } = await api.post('/interactions/', payload)
    return data
  }
)

export const editInteraction = createAsyncThunk(
  'interactions/edit',
  async ({ id, patch }) => {
    const { data } = await api.patch(`/interactions/${id}`, patch)
    return data
  }
)

const interactionsSlice = createSlice({
  name: 'interactions',
  initialState: {
    list: [],
    status: 'idle',
    submitStatus: 'idle',
    lastSaved: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => { state.status = 'loading' })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.list = action.payload
      })
      .addCase(createInteraction.pending, (state) => { state.submitStatus = 'loading' })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.submitStatus = 'succeeded'
        state.lastSaved = action.payload
        state.list.unshift(action.payload)
      })
      .addCase(createInteraction.rejected, (state) => { state.submitStatus = 'failed' })
      .addCase(editInteraction.fulfilled, (state, action) => {
        const idx = state.list.findIndex((i) => i.id === action.payload.id)
        if (idx !== -1) state.list[idx] = action.payload
      })
  },
})

export default interactionsSlice.reducer
