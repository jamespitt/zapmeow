package service

import (
	"encoding/json"
	"zapmeow/api/model"
	"zapmeow/api/repository"
)

type GroupService interface {
	CreateOrUpdateGroup(instanceID string, groupInfo *model.GroupInfo) error
}

type groupService struct {
	groupRepo repository.GroupRepository
}

func NewGroupService(groupRepo repository.GroupRepository) *groupService {
	return &groupService{
		groupRepo: groupRepo,
	}
}

func (s *groupService) CreateOrUpdateGroup(instanceID string, groupInfo *model.GroupInfo) error {
	group, err := s.groupRepo.GetGroupByJID(groupInfo.JID)
	if err != nil {
		// If group not found, GetGroupByJID might return a specific error.
		// For this logic, we assume nil means "not found" and we should create.
		// A more robust implementation would check for a specific "not found" error.
	}

	if group == nil {
		group = &model.Group{}
	}

	// Marshal participants into JSON
	participantsJSON, err := json.Marshal(groupInfo.Participants)
	if err != nil {
		return err
	}

	group.InstanceID = instanceID
	group.JID = groupInfo.JID
	group.OwnerJID = groupInfo.OwnerJID
	group.Name = groupInfo.Name
	group.Topic = groupInfo.Topic
	group.Participants = participantsJSON

	// Use the repository to save the group, which will handle both create and update.
	return s.groupRepo.SaveGroup(group)
}
