import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../api/client'

export const sendChatMessage = createAsyncThunk(
  'chat/send',
  async ({ messages, hcpId, repName }) => {
    const { data } = await api.post('/chat/', {
      messages,
      hcp_id: hcpId,
      rep_name: repName,
    })
    return data
  }
)

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      { role: 'assistant', content: "Hi! Tell me about the visit — who you saw, what was discussed, and any next steps. I'll log it for you." },
    ],
    status: 'idle',
  },
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({ role: 'user', content: action.payload })
    },
    resetChat(state) {
      state.messages = [
        { role: 'assistant', content: "Hi! Tell me about the visit — who you saw, what was discussed, and any next steps. I'll log it for you." },
      ]
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state) => { state.status = 'loading' })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.messages.push({
          role: 'assistant',
          content: action.payload.reply,
          toolCalls: action.payload.tool_calls,
        })
      })
      .addCase(sendChatMessage.rejected, (state) => {
        state.status = 'failed'
        state.messages.push({ role: 'assistant', content: "Sorry, something went wrong reaching the agent." })
      })
  },
})

export const { addUserMessage, resetChat } = chatSlice.actions
export default chatSlice.reducer
