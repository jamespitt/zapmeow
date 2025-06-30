package service

import (
	"zapmeow/api/model"
	"zapmeow/api/repository"

	"go.mau.fi/whatsmeow/types"
)

type GroupService interface {
	CreateOrUpdateGroup(instanceID string, groupInfo *types.GroupInfo) error
}

type groupService struct {
	groupRepo repository.GroupRepository
}

func NewGroupService(groupRepo repository.GroupRepository) *groupService {
	return &groupService{
		groupRepo: groupRepo,
	}
}

func (s *groupService) CreateOrUpdateGroup(instanceID string, groupInfo *types.GroupInfo) error {
	group, err := s.groupRepo.GetGroupByJID(groupInfo.JID.String())
	if err != nil {
		return err
	}

	if group == nil {
		group = &model.Group{}
	}

	group.InstanceID = instanceID
	group.JID = groupInfo.JID.String()
	group.OwnerJID = groupInfo.OwnerJID.String()
	group.GroupName = groupInfo.GroupName.Name
	group.GroupTopic = groupInfo.GroupTopic.Topic
	group.TopicSetBy = groupInfo.GroupTopic.TopicSetBy.String()
	group.TopicSetAt = groupInfo.GroupTopic.TopicSetAt.Unix()
	group.GroupLocked = groupInfo.GroupLocked.IsLocked

	return s.groupRepo.CreateGroup(group)
}
