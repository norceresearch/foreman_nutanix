import { combineReducers } from 'redux';
import EmptyStateReducer from './Components/EmptyState/EmptyStateReducer';

const reducers = {
  foremanNutanixshim: combineReducers({
    emptyState: EmptyStateReducer,
  }),
};

export default reducers;
